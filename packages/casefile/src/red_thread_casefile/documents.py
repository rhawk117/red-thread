"""The case file's nodes in the document tree: an entry with its citation, notes and lead flag."""

from dataclasses import dataclass
from itertools import chain
from typing import TYPE_CHECKING, Literal

from red_thread_core.documents import Term, parse_line
from red_thread_core.dto import DTO
from red_thread_core.util import squeeze

from red_thread_casefile.domain import Cite
from red_thread_casefile.views import Heading, describe_lead, get_shown_verdict
from red_thread_casefile.writers.markdown import write_markdown_entry

if TYPE_CHECKING:
    from red_thread_core.documents import Block, Document, Line, Section

    from red_thread_casefile.domain import Entry, EntryKind, Verdict
    from red_thread_casefile.policy import Finding
    from red_thread_casefile.views import Annotator

type NoteKind = Literal['rests_on', 'refuted_by', 'retires', 'retired_by', 'urgency', 'source']

ENTRIES_TEMPLATE = 'blocks/entries.html.j2'


@dataclass(slots=True, kw_only=True, frozen=True)
class Note:
    kind: NoteKind
    text: str


class Wording(DTO, frozen=True, kw_only=True, forbid_unknown_fields=True):
    headings: tuple[Heading, ...]
    prefixes: dict[NoteKind, str]
    map_note: str
    retired_note: str
    terms: tuple[Term, ...]

    def describe_kind(self, kind: EntryKind) -> str:
        return next(heading.note for heading in self.headings if heading.kind == kind)

    def write_note(self, kind: NoteKind, value: str) -> Note:
        return Note(kind=kind, text=f'{self.prefixes[kind]}{value}')

    def list_caveat_notes(self, entry: Entry) -> tuple[Note, ...]:
        rests_on = entry.rests_on
        refute = entry.refute
        resting = (self.write_note('rests_on', rests_on),) if rests_on is not None else ()
        refuted = (self.write_note('refuted_by', refute),) if refute is not None else ()
        return (*resting, *refuted)


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

    @property
    def template(self) -> str:
        return ENTRIES_TEMPLATE

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
