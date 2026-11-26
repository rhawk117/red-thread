"""The case file's nodes in the document tree: an entry with its citation, notes and lead flag."""

from dataclasses import dataclass
from itertools import chain
from typing import TYPE_CHECKING, Literal

from red_thread_core.documents import parse_line
from red_thread_core.util import squeeze

from red_thread_casefile.domain import Cite
from red_thread_casefile.views import describe_lead, get_shown_verdict
from red_thread_casefile.writers.markdown import write_markdown_entry
from red_thread_casefile.writers.markup import write_entries

if TYPE_CHECKING:
    from string.templatelib import Template

    from red_thread_core.documents import Block, Document, Line, Section

    from red_thread_casefile.domain import Entry, EntryKind, Verdict
    from red_thread_casefile.policy import Finding
    from red_thread_casefile.views import Annotator

type NoteKind = Literal['rests_on', 'refuted_by', 'retires', 'retired_by', 'urgency', 'source']


@dataclass(slots=True, kw_only=True, frozen=True)
class NoteLabel:
    kind: NoteKind
    prefix: str


NOTE_LABELS = (
    NoteLabel(kind='rests_on', prefix='rests on: '),
    NoteLabel(kind='refuted_by', prefix='refuted by: '),
    NoteLabel(kind='retires', prefix='retires: '),
    NoteLabel(kind='retired_by', prefix='retired by '),
    NoteLabel(kind='urgency', prefix=''),
    NoteLabel(kind='source', prefix=''),
)


@dataclass(slots=True, kw_only=True, frozen=True)
class Note:
    kind: NoteKind
    value: str

    @property
    def text(self) -> str:
        prefix = next(label.prefix for label in NOTE_LABELS if label.kind == self.kind)
        return f'{prefix}{self.value}'


@dataclass(slots=True, kw_only=True, frozen=True)
class Citation:
    target: str
    quote: str | None = None
    finding: Finding | None = None

    @property
    def is_url(self) -> bool:
        return Cite(raw=self.target).is_url


@dataclass(slots=True, kw_only=True, frozen=True)
class EntryNode:
    ref: str
    kind: EntryKind
    claim: Line
    thread: str | None = None
    verdict: Verdict | None = None
    round: int
    at: str
    citation: Citation | None = None
    notes: tuple[Note, ...] = ()
    lead: str | None = None
    diagram: str | None = None

    @property
    def flags(self) -> tuple[str, ...]:
        if self.lead is None:
            return ()
        return (describe_lead(self.lead),)


@dataclass(slots=True, kw_only=True, frozen=True)
class EntryList:
    entries: tuple[EntryNode, ...]

    @property
    def count(self) -> int:
        return len(self.entries)

    def write_html(self) -> Template:
        return write_entries(self.entries)

    def write_markdown(self) -> tuple[str, ...]:
        return tuple(map(write_markdown_entry, self.entries))


def list_section_entries(section: Section) -> tuple[EntryNode, ...]:
    lists = (block.entries for block in section.blocks if isinstance(block, EntryList))
    return tuple(chain.from_iterable(lists))


def list_document_entries(document: Document) -> tuple[EntryNode, ...]:
    return tuple(chain.from_iterable(map(list_section_entries, document.sections)))


def list_entries_block(entries: tuple[EntryNode, ...]) -> tuple[Block, ...]:
    if not entries:
        return ()
    return (EntryList(entries=entries),)


def list_caveat_notes(entry: Entry) -> tuple[Note, ...]:
    rests_on = (Note(kind='rests_on', value=entry.rests_on),) if entry.rests_on is not None else ()
    refuted = (Note(kind='refuted_by', value=entry.refute),) if entry.refute is not None else ()
    return (*rests_on, *refuted)


@dataclass(slots=True, kw_only=True, frozen=True)
class EntryBuilder:
    annotator: Annotator

    def create_citation(self, entry: Entry) -> Citation | None:
        if entry.cite is None:
            return None
        return Citation(target=entry.cite, quote=entry.quote, finding=self.annotator.find(entry))

    def build(self, entry: Entry, notes: tuple[Note, ...] = ()) -> EntryNode:
        return EntryNode(
            ref=entry.ref,
            kind=entry.kind,
            claim=parse_line(squeeze(entry.text)),
            round=entry.round,
            at=entry.at,
            thread=entry.thread,
            verdict=get_shown_verdict(entry),
            citation=self.create_citation(entry),
            notes=notes,
            lead=self.annotator.get_recorded_head(entry),
            diagram=entry.diagram,
        )
