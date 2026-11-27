"""The values a case file holds: the case, its rounds and findings, and where each one sits."""

import re
from datetime import date, datetime
from itertools import chain
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Annotated, Literal

import msgspec
from red_thread_core.dto import DTO
from red_thread_core.timekeeping import write_compact_day

if TYPE_CHECKING:
    from collections.abc import Sequence

type FindingKind = Literal[
    'known', 'open', 'decision', 'hypothesis', 'ruled_out', 'resource', 'next'
]
type Verdict = Literal['VERIFIED', 'INFERRED', 'NEEDS-ANALYSIS', 'BLOCKED']
type CaseKind = Literal['root-cause', 'claim', 'research', 'survey']
type CitationForm = Literal['path', 'url', 'other']
type Filled = Annotated[str, msgspec.Meta(pattern=r'\S')]

FINDING_KINDS: tuple[FindingKind, ...] = (
    'known',
    'open',
    'decision',
    'hypothesis',
    'ruled_out',
    'resource',
    'next',
)
VERDICTS: tuple[Verdict, ...] = ('VERIFIED', 'INFERRED', 'NEEDS-ANALYSIS', 'BLOCKED')
CASE_KINDS: tuple[CaseKind, ...] = ('root-cause', 'claim', 'research', 'survey')
OWNER = 'user'
STATE_DIRECTORY = '.red-thread'
CITE_URL_SCHEMES = ('http://', 'https://')
PAGE_URL_SCHEME = 'https://'
SHORT_HEAD = 7
NO_HEAD = 'none'
PROGRAM = 'redthread-casefile'
SLUG_WORDS = 5
PATH_CITE = re.compile(r'(?P<path>[^\s:#]+):(?P<line>[1-9]\d*)(?:-\d+)?')
THREAD_NAME = re.compile(r'T[1-9]\d*')
SLUG_BREAK = re.compile(r'[^a-z0-9]+')
CASE_FILE = 'case.md'
THREAD_HOME = 'threads'
THREAD_SUFFIX = '.md'
TITLE_MARK = '# '
ROUND_MARK = '## '
FINDING_MARK = '### '
BLOCK_OPEN = '```yaml'
BLOCK_CLOSE = '```'
STAMP_SEPARATOR = ' · '
ROUND_WORD = 'Round'
ROUND_HEADING = re.compile(
    r'##\s+Round\s+(?P<round>\d+)\s+·\s+(?P<day>\d{4}-\d{2}-\d{2})\s+·\s+'
    r'(?P<head>[0-9a-f]{7,40}|none)'
)
FINDING_HEADING = re.compile(r'###\s+e(?P<finding_number>[1-9]\d*)')
OPTIONAL_TEXT_FIELDS = ('cite', 'quote', 'addr', 'rests_on', 'refute', 'diagram')
TEXT_FIELDS = ('text', *OPTIONAL_TEXT_FIELDS)


def order_thread(name: str) -> int:
    return int(name[1:])


def is_current(recorded: str | None, head: str | None) -> bool:
    if recorded is None or head is None:
        return recorded == head
    return head.startswith(recorded)


def shorten_head(head: str | None, missing: str = NO_HEAD) -> str:
    if head is None:
        return missing
    return head[:SHORT_HEAD]


def find_member[T](value: object, members: Sequence[T]) -> T | None:
    return next((member for member in members if member == value), None)


def build_case_id(created: datetime, label: str) -> str:
    day = write_compact_day(created.date())
    words = SLUG_BREAK.sub(' ', label.lower()).split()[:SLUG_WORDS]
    return '-'.join((day, *words))


class Citation(DTO, frozen=True, kw_only=True, gc=False):
    raw: str

    @property
    def is_url(self) -> bool:
        return self.raw.startswith(CITE_URL_SCHEMES)

    @property
    def located(self) -> re.Match[str] | None:
        if self.is_url:
            return None
        return PATH_CITE.fullmatch(self.raw.strip())

    @property
    def path(self) -> str | None:
        if not (located := self.located):
            return None
        path = PurePosixPath(located['path'])
        if path.is_absolute() or '..' in path.parts:
            return None
        return str(path)

    @property
    def line(self) -> int | None:
        located = self.located
        if not located or self.path is None:
            return None
        return int(located['line'])

    @property
    def form(self) -> CitationForm:
        if self.is_url:
            return 'url'
        if self.path is not None:
            return 'path'
        return 'other'


class FindingLocation(DTO, frozen=True, kw_only=True, gc=False):
    file: str
    line: int
    finding_id: str | None = None

    @property
    def label(self) -> str:
        place = f'{self.file}:{self.line}'
        return place if self.finding_id is None else f'{place} {self.finding_id}'


class RoundStamp(DTO, frozen=True, kw_only=True, gc=False):
    number: int
    day: date
    head: str | None = None

    @property
    def heading(self) -> str:
        parts = (f'{ROUND_WORD} {self.number}', self.day.isoformat(), shorten_head(self.head))
        return f'{ROUND_MARK}{STAMP_SEPARATOR.join(parts)}'


class LedgerSource(DTO, frozen=True, kw_only=True, gc=False):
    name: str
    thread: str | None
    text: str


class FindingBlock(
    DTO,
    frozen=True,
    kw_only=True,
    gc=False,
    omit_defaults=True,
    forbid_unknown_fields=True,
):
    kind: FindingKind
    text: Filled
    source: Filled
    verdict: Verdict | None = None
    citation: Filled | None = msgspec.field(default=None, name='cite')
    quote: Filled | None = None
    code_address: Filled | None = msgspec.field(default=None, name='addr')
    rests_on: Filled | None = None
    refuted_if: Filled | None = msgspec.field(default=None, name='refute')
    diagram: Filled | None = None
    supersedes: tuple[str, ...] = ()


class CaseFinding(
    DTO,
    frozen=True,
    kw_only=True,
    gc=False,
    omit_defaults=True,
    forbid_unknown_fields=True,
):
    finding_number: int
    round: int
    kind: FindingKind
    text: str
    source: str
    at: date
    head: str | None = None
    verdict: Verdict | None = None
    citation: str | None = msgspec.field(default=None, name='cite')
    quote: str | None = None
    code_address: str | None = msgspec.field(default=None, name='addr')
    rests_on: str | None = None
    refuted_if: str | None = msgspec.field(default=None, name='refute')
    diagram: str | None = None
    supersedes: tuple[str, ...] = ()
    thread: str | None = None

    @property
    def finding_id(self) -> str:
        if self.thread is None:
            return f'e{self.finding_number}'
        return f'{self.thread}.e{self.finding_number}'


class Capabilities(DTO, frozen=True, kw_only=True, gc=False, forbid_unknown_fields=True):
    languages: tuple[str, ...] = ()


class Case(DTO, frozen=True, kw_only=True, gc=False, forbid_unknown_fields=True):
    id: str
    target: str
    kind: CaseKind
    bar: str
    created: datetime
    publish: bool = False
    head: str | None = None
    page_url: str | None = None
    capabilities: Capabilities = msgspec.field(default_factory=Capabilities)


class CaseLedger(DTO, frozen=True, kw_only=True, gc=False):
    findings: tuple[CaseFinding, ...] = ()

    @property
    def finding_ids(self) -> frozenset[str]:
        return frozenset(finding.finding_id for finding in self.findings)

    @property
    def retired(self) -> frozenset[str]:
        return frozenset(chain.from_iterable(finding.supersedes for finding in self.findings))

    @property
    def live(self) -> tuple[CaseFinding, ...]:
        retired = self.retired
        return tuple(finding for finding in self.findings if finding.finding_id not in retired)

    @property
    def last_round(self) -> int:
        return max((finding.round for finding in self.findings), default=0)

    @property
    def threads(self) -> tuple[str, ...]:
        names = {finding.thread for finding in self.findings if finding.thread is not None}
        return tuple(sorted(names, key=order_thread))

    def select(self, kind: FindingKind) -> tuple[CaseFinding, ...]:
        return tuple(finding for finding in self.live if finding.kind == kind)

    def count_in(self, thread: str | None) -> int:
        return sum(1 for finding in self.findings if finding.thread == thread)

    def describe_threads(self) -> str:
        return ', '.join(f'{name} ({self.count_in(name)})' for name in self.threads)


class LocatedFinding(DTO, frozen=True, kw_only=True, gc=False):
    finding: CaseFinding
    location: FindingLocation


class CaseRecord(DTO, frozen=True, kw_only=True, gc=False):
    case: Case
    ledger: CaseLedger
