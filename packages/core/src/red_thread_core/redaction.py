"""Secret redaction backed by detect-secrets, applied to every free-text field."""

import re
from dataclasses import dataclass
from functools import reduce
from operator import attrgetter
from typing import TYPE_CHECKING, TypeIs

from detect_secrets.core.plugins.util import get_mapping_from_secret_type_to_class
from detect_secrets.plugins.base import RegexBasedDetector
from detect_secrets.plugins.ip_public import IPPublicDetector
from detect_secrets.plugins.keyword import KeywordDetector

from red_thread_core.dto import DTO

if TYPE_CHECKING:
    from collections.abc import Iterator

    from detect_secrets.plugins.base import BasePlugin

type Span = tuple[int, int]

EDGE = re.compile(r'[\s"\'`]')
BOUNDARY = re.compile(r'[\s"\'`/:@=,;()<>\[\]{}]')
MARKER = re.compile(r'\[REDACTED:[a-z0-9-]+\]')


class Hit(DTO, frozen=True, kw_only=True, gc=False):
    start: int
    end: int
    label: str

    @property
    def order(self) -> Span:
        return self.start, -self.end

    def overlaps(self, span: Span) -> bool:
        return self.start < span[1] and span[0] < self.end


class Redaction(DTO, frozen=True, kw_only=True, gc=False):
    text: str
    hits: int


def label_for(secret_type: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', secret_type.lower()).strip('-')


def is_edge(text: str, index: int) -> bool:
    return bool(EDGE.match(text, index))


def is_inside(text: str, index: int) -> bool:
    return not BOUNDARY.match(text, index)


def trim_edges(text: str, span: Span) -> Span:
    start, end = span
    while start < end and is_edge(text, start):
        start += 1
    while end > start and is_edge(text, end - 1):
        end -= 1
    return start, end


def grow_inside(text: str, span: Span) -> Span:
    start, end = span
    while start > 0 and is_inside(text, start - 1):
        start -= 1
    while end < len(text) and is_inside(text, end):
        end += 1
    return start, end


def widen(text: str, span: Span) -> Span:
    return grow_inside(text, trim_edges(text, span))


def widen_hit(text: str, hit: Hit) -> Hit:
    start, end = widen(text, (hit.start, hit.end))
    return hit.replace_with(start=start, end=end)


def find_spans(pattern: re.Pattern[str], text: str) -> Iterator[Span]:
    group = 1 if pattern.groups else 0
    spans = (match.span(group) for match in pattern.finditer(text))
    return (span for span in spans if span[0] >= 0)


@dataclass(slots=True, kw_only=True, frozen=True)
class Detector:
    label: str
    patterns: tuple[re.Pattern[str], ...]

    def find(self, text: str) -> Iterator[Hit]:
        for pattern in self.patterns:
            for start, end in find_spans(pattern, text):
                yield Hit(start=start, end=end, label=self.label)


def absorb(merged: list[Hit], hit: Hit) -> list[Hit]:
    last = merged[-1] if merged else None
    if last is None or hit.start >= last.end:
        return [*merged, hit]

    return [*merged[:-1], last.replace_with(end=max(last.end, hit.end))]


def write_over(text: str, hit: Hit) -> str:
    return f'{text[: hit.start]}[REDACTED:{hit.label}]{text[hit.end :]}'


@dataclass(slots=True, kw_only=True, frozen=True)
class SecretPatterns:
    detectors: tuple[Detector, ...]
    keywords: KeywordDetector

    def find_keyword_hits(self, text: str) -> Iterator[Hit]:
        label = label_for(self.keywords.secret_type)
        for secret in set(self.keywords.analyze_string(text)):
            for match in re.finditer(re.escape(secret), text):
                yield Hit(start=match.start(), end=match.end(), label=label)

    def find_hits(self, text: str) -> Iterator[Hit]:
        for detector in self.detectors:
            yield from detector.find(text)
        yield from self.find_keyword_hits(text)

    def locate(self, text: str) -> list[Hit]:
        markers = tuple(match.span() for match in MARKER.finditer(text))
        widened = (widen_hit(text, hit) for hit in self.find_hits(text))
        fresh = (
            hit for hit in widened if hit.start < hit.end and not any(map(hit.overlaps, markers))
        )
        return reduce(absorb, sorted(fresh, key=attrgetter('order')), [])

    def scrub(self, text: str) -> Redaction:
        hits = self.locate(text)
        return Redaction(text=reduce(write_over, reversed(hits), text), hits=len(hits))

    def scrub_text(self, text: str) -> str:
        return self.scrub(text).text


EXTRA_DETECTORS = (
    Detector(
        label='private-key',
        patterns=(
            re.compile(
                r'-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----.*?'
                r'-----END [A-Z ]*PRIVATE KEY(?: BLOCK)?-----',
                re.DOTALL,
            ),
        ),
    ),
    Detector(label='github-token', patterns=(re.compile(r'\bgithub_pat_\w{20,}'),)),
    Detector(
        label='stripe-access-key', patterns=(re.compile(r'\b[rs]k_(?:live|test)_[A-Za-z0-9]{16,}'),)
    ),
    Detector(label='api-key', patterns=(re.compile(r'\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}'),)),
    Detector(label='bearer-token', patterns=(re.compile(r'\bBearer ([A-Za-z0-9._~+/-]{12,}=*)'),)),
    Detector(label='basic-auth-credentials', patterns=(re.compile(r'://[^/\s:@]+:([^@\s]+)@'),)),
    Detector(
        label='secret-keyword',
        patterns=(
            re.compile(
                r'(?i)(?<![A-Z0-9_])[A-Z0-9_]*(?:token|secret|password|passwd|api_?key)[A-Z0-9_]*'
                r'["\']?\s*[:=]\s*["\']?((?!\d+(?:[\s,;"\']|$))[^\s,;"\']{6,})'
            ),
        ),
    ),
)


def is_pattern_plugin(plugin: type[BasePlugin]) -> TypeIs[type[RegexBasedDetector]]:
    return issubclass(plugin, RegexBasedDetector) and plugin is not IPPublicDetector


def create_plugin(plugin: type[RegexBasedDetector]) -> RegexBasedDetector:
    return plugin()


def library_detector(plugin: RegexBasedDetector) -> Detector:
    return Detector(label=label_for(plugin.secret_type), patterns=tuple(plugin.denylist))


def create_secret_patterns() -> SecretPatterns:
    plugins = get_mapping_from_secret_type_to_class().values()
    library = map(library_detector, map(create_plugin, filter(is_pattern_plugin, plugins)))
    return SecretPatterns(detectors=(*EXTRA_DETECTORS, *library), keywords=KeywordDetector())
