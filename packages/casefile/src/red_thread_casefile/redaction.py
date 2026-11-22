"""Secret redaction applied to every free-text field before it is stored."""

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Mapping

type PatternName = Literal[
    'private-key',
    'aws-key',
    'github-token',
    'slack-token',
    'stripe-key',
    'api-key',
    'jwt',
    'bearer',
    'url-credentials',
    'assignment',
]

SECRET_PATTERNS: tuple[tuple[PatternName, re.Pattern[str]], ...] = (
    (
        'private-key',
        re.compile(
            r'-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----',
            re.DOTALL,
        ),
    ),
    ('aws-key', re.compile(r'\b(?:AKIA|ASIA)[0-9A-Z]{16}\b')),
    ('github-token', re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_\w{20,})')),
    ('slack-token', re.compile(r'\bxox[abposr]-[A-Za-z0-9-]{10,}')),
    ('stripe-key', re.compile(r'\b[rs]k_(?:live|test)_[A-Za-z0-9]{16,}\b')),
    ('api-key', re.compile(r'\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}')),
    ('jwt', re.compile(r'\beyJ[\w-]+\.[\w-]+\.[\w-]+')),
    ('bearer', re.compile(r'\bBearer [A-Za-z0-9._~+/-]{12,}=*')),
    ('url-credentials', re.compile(r'(?<=://)(?!\[REDACTED:)[^/\s:@]+:[^@\s]+(?=@)')),
    (
        'assignment',
        re.compile(
            r'(?i)(?<![A-Z0-9_])'
            r'(?:(?>[A-Z0-9_]*?(?:password|passwd|secret|token|api_?key))[A-Z0-9_]*+'
            r'|[A-Z0-9_]*+(?<=api)-key[A-Z0-9_]*+)'
            r'["\']?\s*[:=]\s*["\']?(?!\d+(?:[\s,;"\']|$))[^\s,;"\']{6,}'
        ),
    ),
)


@dataclass(slots=True, kw_only=True, frozen=True)
class Redaction:
    text: str
    hits: int


@dataclass(slots=True, kw_only=True, frozen=True)
class SecretPatterns:
    by_name: Mapping[PatternName, re.Pattern[str]]

    def scrub(self, text: str) -> Redaction:
        hits = 0
        for name, pattern in self.by_name.items():
            text, replaced = pattern.subn(f'[REDACTED:{name}]', text)
            hits += replaced
        return Redaction(text=text, hits=hits)


def create_secret_patterns() -> SecretPatterns:
    return SecretPatterns(by_name=MappingProxyType(dict(SECRET_PATTERNS)))
