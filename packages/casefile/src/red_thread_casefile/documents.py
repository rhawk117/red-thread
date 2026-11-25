"""The document tree between the ledger and the writers of the page and the Markdown outputs."""

import re
from dataclasses import dataclass
from itertools import chain
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

from red_thread_casefile.domain import Cite
from red_thread_casefile.util import squeeze
from red_thread_casefile.views import LEAD_FLAG_PREFIX, get_shown_verdict

if TYPE_CHECKING:
    from red_thread_casefile.domain import Entry, EntryKind, Verdict
    from red_thread_casefile.policy import Finding
    from red_thread_casefile.views import Annotator

type NoteKind = Literal['rests_on', 'refuted_by', 'retires', 'retired_by', 'urgency', 'source']

CODE_SPAN = re.compile(r'`([^`]+)`')
LEAD_PREFIX = f'{LEAD_FLAG_PREFIX}recorded at '


@runtime_checkable
class InlineWriter[T](Protocol):
    def write_text(self, node: Text) -> T: ...

    def write_code(self, node: Code) -> T: ...

    def write_link(self, node: Link) -> T: ...


@runtime_checkable
class BlockWriter[T](Protocol):
    def write_paragraph(self, node: Paragraph) -> T: ...

    def write_entries(self, node: EntryList) -> T: ...

    def write_points(self, node: PointList) -> T: ...

    def write_flowchart(self, node: Flowchart) -> T: ...


@dataclass(slots=True, kw_only=True, frozen=True)
class Text:
    value: str

    def write[T](self, writer: InlineWriter[T]) -> T:
        return writer.write_text(self)


@dataclass(slots=True, kw_only=True, frozen=True)
class Code:
    value: str

    def write[T](self, writer: InlineWriter[T]) -> T:
        return writer.write_code(self)


@dataclass(slots=True, kw_only=True, frozen=True)
class Link:
    url: str

    def write[T](self, writer: InlineWriter[T]) -> T:
        return writer.write_link(self)


type Inline = Text | Code | Link
type Line = tuple[Inline, ...]


def create_inline(index: int, piece: str) -> Inline:
    if index % 2:
        return Code(value=piece)
    return Text(value=piece)


def parse_line(text: str) -> Line:
    pieces = enumerate(CODE_SPAN.split(text))
    return tuple(create_inline(index, piece) for index, piece in pieces if piece)


def parse_value(text: str) -> Line:
    if Cite(raw=text).is_url:
        return (Link(url=text),)
    return parse_line(text)


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
        return (f'{LEAD_PREFIX}{self.lead}',)


@dataclass(slots=True, kw_only=True, frozen=True)
class Paragraph:
    line: Line

    def write[T](self, writer: BlockWriter[T]) -> T:
        return writer.write_paragraph(self)


@dataclass(slots=True, kw_only=True, frozen=True)
class EntryList:
    entries: tuple[EntryNode, ...]

    def write[T](self, writer: BlockWriter[T]) -> T:
        return writer.write_entries(self)


@dataclass(slots=True, kw_only=True, frozen=True)
class PointList:
    points: tuple[Line, ...]

    def write[T](self, writer: BlockWriter[T]) -> T:
        return writer.write_points(self)


@dataclass(slots=True, kw_only=True, frozen=True)
class Flowchart:
    lines: tuple[str, ...]

    def write[T](self, writer: BlockWriter[T]) -> T:
        return writer.write_flowchart(self)


type Block = Paragraph | EntryList | PointList | Flowchart


@dataclass(slots=True, kw_only=True, frozen=True)
class Section:
    title: str
    blocks: tuple[Block, ...] = ()
    kind: EntryKind | None = None
    note: str = ''
    folded: bool = False

    @property
    def entries(self) -> tuple[EntryNode, ...]:
        lists = (block.entries for block in self.blocks if isinstance(block, EntryList))
        return tuple(chain.from_iterable(lists))


@dataclass(slots=True, kw_only=True, frozen=True)
class Fact:
    label: str
    value: Line
    wide: bool = False


@dataclass(slots=True, kw_only=True, frozen=True)
class Document:
    title: str
    summary: tuple[Line, ...] = ()
    facts: tuple[Fact, ...] = ()
    sections: tuple[Section, ...] = ()
    appendix: tuple[Section, ...] = ()

    @property
    def entries(self) -> tuple[EntryNode, ...]:
        return tuple(chain.from_iterable(section.entries for section in self.sections))


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
