"""The values a case file holds: the case, its entries and the drafts agents submit."""

import re
from dataclasses import dataclass
from itertools import chain
from pathlib import PurePosixPath
from typing import Literal

import msgspec

type EntryKind = Literal['known', 'open', 'decision', 'hypothesis', 'ruled_out', 'resource', 'next']
type Verdict = Literal['VERIFIED', 'INFERRED', 'NEEDS-ANALYSIS', 'BLOCKED']
type CaseKind = Literal['root-cause', 'claim', 'research', 'survey']
type CiteForm = Literal['path', 'url', 'other']

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
SLUG_WORDS = 5
PATH_CITE = re.compile(r'(?P<path>[^\s:#]+):(?P<line>[1-9]\d*)(?:-\d+)?')
THREAD_NAME = re.compile(r'T[1-9]\d*')
SLUG_BREAK = re.compile(r'[^a-z0-9]+')


def order_thread(name: str) -> int:
    return int(name[1:])


def build_case_id(created: str, label: str) -> str:
    day = created[:10].replace('-', '')
    words = SLUG_BREAK.sub(' ', label.lower()).split()[:SLUG_WORDS]
    return '-'.join((day, *words))


@dataclass(slots=True, kw_only=True, frozen=True)
class Cite:
    raw: str

    @property
    def is_url(self) -> bool:
        return self.raw.startswith(('http://', 'https://'))

    @property
    def located(self) -> re.Match[str] | None:
        if self.is_url:
            return None
        return PATH_CITE.fullmatch(self.raw.strip())

    @property
    def path(self) -> str | None:
        if (located := self.located) is None:
            return None
        path = PurePosixPath(located['path'])
        if path.is_absolute() or '..' in path.parts:
            return None
        return str(path)

    @property
    def line(self) -> int | None:
        located = self.located
        if located is None or self.path is None:
            return None
        return int(located['line'])

    @property
    def form(self) -> CiteForm:
        if self.is_url:
            return 'url'
        if self.path is not None:
            return 'path'
        return 'other'


@dataclass(slots=True, kw_only=True, frozen=True)
class Draft:
    position: int
    kind: EntryKind
    text: str
    source: str
    verdict: Verdict | None = None
    cite: str | None = None
    quote: str | None = None
    addr: str | None = None
    rests_on: str | None = None
    refute: str | None = None
    diagram: str | None = None
    supersedes: tuple[str, ...] = ()


class Entry(
    msgspec.Struct,
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


class Capabilities(msgspec.Struct, frozen=True, kw_only=True, gc=False):
    languages: tuple[str, ...] = ()
    navigation_tool: bool = False


class Case(msgspec.Struct, frozen=True, kw_only=True, gc=False):
    id: str
    target: str
    kind: CaseKind
    bar: str
    created: str
    publish: bool = False
    head: str | None = None
    page_url: str | None = None
    capabilities: Capabilities = msgspec.field(default_factory=Capabilities)


@dataclass(slots=True, kw_only=True, frozen=True)
class Ledger:
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
