"""The values a case file holds: the case, its rounds and entries, and where each one sits."""

import re
from datetime import date
from itertools import chain
from pathlib import PurePosixPath
from typing import Annotated, Literal

import msgspec
from red_thread_core.dto import DTO

from red_thread_casefile.errors import InvalidTimestampError

type EntryKind = Literal['known', 'open', 'decision', 'hypothesis', 'ruled_out', 'resource', 'next']
type Verdict = Literal['VERIFIED', 'INFERRED', 'NEEDS-ANALYSIS', 'BLOCKED']
type CaseKind = Literal['root-cause', 'claim', 'research', 'survey']
type CiteForm = Literal['path', 'url', 'other']
type Filled = Annotated[str, msgspec.Meta(pattern=r'\S')]

ENTRY_KINDS: tuple[EntryKind, ...] = (
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
DATE_WIDTH = 10
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
ENTRY_MARK = '### '
BLOCK_OPEN = '```yaml'
BLOCK_CLOSE = '```'
STAMP_SEPARATOR = ' · '
ROUND_WORD = 'Round'
ROUND_HEADING = re.compile(
    r'##\s+Round\s+(?P<round>\d+)\s+·\s+(?P<day>\d{4}-\d{2}-\d{2})\s+·\s+'
    r'(?P<head>[0-9a-f]{7,40}|none)'
)
ENTRY_HEADING = re.compile(r'###\s+e(?P<seq>[1-9]\d*)')
OPTIONAL_TEXT_FIELDS = ('cite', 'quote', 'addr', 'rests_on', 'refute', 'diagram')
TEXT_FIELDS = ('text', *OPTIONAL_TEXT_FIELDS)


def order_thread(name: str) -> int:
    return int(name[1:])


def date_of(timestamp: str) -> str:
    try:
        return date.fromisoformat(timestamp[:DATE_WIDTH]).isoformat()
    except ValueError as error:
        raise InvalidTimestampError(timestamp=timestamp) from error


def is_day(text: str) -> bool:
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True


def is_current(recorded: str | None, head: str | None) -> bool:
    if recorded is None or head is None:
        return recorded == head
    return head.startswith(recorded)


def shorten_head(head: str | None, missing: str = NO_HEAD) -> str:
    if head is None:
        return missing
    return head[:SHORT_HEAD]


def find_member[T](value: object, members: tuple[T, ...]) -> T | None:
    return next((member for member in members if member == value), None)


def build_case_id(created: str, label: str) -> str:
    day = date_of(created).replace('-', '')
    words = SLUG_BREAK.sub(' ', label.lower()).split()[:SLUG_WORDS]
    return '-'.join((day, *words))


class Cite(DTO, frozen=True, kw_only=True, gc=False):
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
    def form(self) -> CiteForm:
        if self.is_url:
            return 'url'
        if self.path is not None:
            return 'path'
        return 'other'


class Spot(DTO, frozen=True, kw_only=True, gc=False):
    file: str
    line: int
    ref: str | None = None

    @property
    def label(self) -> str:
        place = f'{self.file}:{self.line}'
        return place if self.ref is None else f'{place} {self.ref}'


class RoundStamp(DTO, frozen=True, kw_only=True, gc=False):
    number: int
    day: str
    head: str | None = None

    @property
    def heading(self) -> str:
        parts = (f'{ROUND_WORD} {self.number}', self.day, shorten_head(self.head))
        return f'{ROUND_MARK}{STAMP_SEPARATOR.join(parts)}'


class LedgerSource(DTO, frozen=True, kw_only=True, gc=False):
    name: str
    thread: str | None
    text: str


class EntryRecord(
    DTO,
    frozen=True,
    kw_only=True,
    gc=False,
    omit_defaults=True,
    forbid_unknown_fields=True,
):
    kind: EntryKind
    text: Filled
    source: Filled
    verdict: Verdict | None = None
    cite: Filled | None = None
    quote: Filled | None = None
    addr: Filled | None = None
    rests_on: Filled | None = None
    refute: Filled | None = None
    diagram: Filled | None = None
    supersedes: tuple[str, ...] = ()


class Entry(
    DTO,
    frozen=True,
    kw_only=True,
    gc=False,
    omit_defaults=True,
    forbid_unknown_fields=True,
):
    seq: int
    round: int
    kind: EntryKind
    text: str
    source: str
    at: str
    head: str | None = None
    verdict: Verdict | None = None
    cite: str | None = None
    quote: str | None = None
    addr: str | None = None
    rests_on: str | None = None
    refute: str | None = None
    diagram: str | None = None
    supersedes: tuple[str, ...] = ()
    thread: str | None = None

    @property
    def ref(self) -> str:
        if self.thread is None:
            return f'e{self.seq}'
        return f'{self.thread}.e{self.seq}'


class Capabilities(DTO, frozen=True, kw_only=True, gc=False, forbid_unknown_fields=True):
    languages: tuple[str, ...] = ()


class Case(DTO, frozen=True, kw_only=True, gc=False, forbid_unknown_fields=True):
    id: str
    target: str
    kind: CaseKind
    bar: str
    created: str
    publish: bool = False
    head: str | None = None
    page_url: str | None = None
    capabilities: Capabilities = msgspec.field(default_factory=Capabilities)


class Ledger(DTO, frozen=True, kw_only=True, gc=False):
    entries: tuple[Entry, ...] = ()

    @property
    def refs(self) -> frozenset[str]:
        return frozenset(entry.ref for entry in self.entries)

    @property
    def retired(self) -> frozenset[str]:
        return frozenset(chain.from_iterable(entry.supersedes for entry in self.entries))

    @property
    def live(self) -> tuple[Entry, ...]:
        retired = self.retired
        return tuple(entry for entry in self.entries if entry.ref not in retired)

    @property
    def last_round(self) -> int:
        return max((entry.round for entry in self.entries), default=0)

    @property
    def threads(self) -> tuple[str, ...]:
        names = {entry.thread for entry in self.entries if entry.thread is not None}
        return tuple(sorted(names, key=order_thread))

    def select(self, kind: EntryKind) -> tuple[Entry, ...]:
        return tuple(entry for entry in self.live if entry.kind == kind)

    def count_in(self, thread: str | None) -> int:
        return sum(1 for entry in self.entries if entry.thread == thread)

    def describe_threads(self) -> str:
        return ', '.join(f'{name} ({self.count_in(name)})' for name in self.threads)


class Placed(DTO, frozen=True, kw_only=True, gc=False):
    entry: Entry
    spot: Spot


class CaseRecord(DTO, frozen=True, kw_only=True, gc=False):
    case: Case
    ledger: Ledger
