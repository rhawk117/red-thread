"""The document tree that pages and Markdown are written from, open to blocks of any package."""

import re
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from red_thread_core.writers.markdown import write_markdown_line

CODE_SPAN = re.compile(r'`([^`]+)`')
URL_SCHEMES = ('http://', 'https://')
PARAGRAPH_TEMPLATE = 'blocks/paragraph.html.j2'
POINTS_TEMPLATE = 'blocks/points.html.j2'
FLOWCHART_TEMPLATE = 'blocks/flowchart.html.j2'
LISTING_TEMPLATE = 'blocks/listing.html.j2'

type InlineKind = Literal['text', 'code', 'link']


@runtime_checkable
class InlineWriter[T](Protocol):
    def write_text(self, node: Text) -> T: ...

    def write_code(self, node: Code) -> T: ...

    def write_link(self, node: Link) -> T: ...


@runtime_checkable
class Block(Protocol):
    @property
    def count(self) -> int: ...

    @property
    def template(self) -> str: ...

    def write_markdown(self) -> tuple[str, ...]: ...


@dataclass(slots=True, kw_only=True, frozen=True)
class Text:
    value: str

    @property
    def kind(self) -> InlineKind:
        return 'text'

    def write[T](self, writer: InlineWriter[T]) -> T:
        return writer.write_text(self)


@dataclass(slots=True, kw_only=True, frozen=True)
class Code:
    value: str

    @property
    def kind(self) -> InlineKind:
        return 'code'

    def write[T](self, writer: InlineWriter[T]) -> T:
        return writer.write_code(self)


@dataclass(slots=True, kw_only=True, frozen=True)
class Link:
    url: str
    label: str = ''

    @property
    def kind(self) -> InlineKind:
        return 'link'

    @property
    def shown(self) -> str:
        return self.label or self.url

    def write[T](self, writer: InlineWriter[T]) -> T:
        return writer.write_link(self)


type Inline = Text | Code | Link
type Line = tuple[Inline, ...]


def is_url(text: str) -> bool:
    return text.startswith(URL_SCHEMES)


def create_inline(index: int, piece: str) -> Inline:
    if index % 2:
        return Code(value=piece)
    return Text(value=piece)


def parse_line(text: str) -> Line:
    pieces = enumerate(CODE_SPAN.split(text))
    return tuple(create_inline(index, piece) for index, piece in pieces if piece)


def parse_value(text: str) -> Line:
    if is_url(text):
        return (Link(url=text),)
    return parse_line(text)


@dataclass(slots=True, kw_only=True, frozen=True)
class Paragraph:
    line: Line
    count: int = 0

    @property
    def template(self) -> str:
        return PARAGRAPH_TEMPLATE

    def write_markdown(self) -> tuple[str, ...]:
        return (write_markdown_line(self.line),)


@dataclass(slots=True, kw_only=True, frozen=True)
class PointList:
    points: tuple[Line, ...]
    count: int = 0

    @property
    def template(self) -> str:
        return POINTS_TEMPLATE

    def write_markdown(self) -> tuple[str, ...]:
        return tuple(f'- {write_markdown_line(point)}' for point in self.points)


@dataclass(slots=True, kw_only=True, frozen=True)
class Flowchart:
    lines: tuple[str, ...]
    count: int = 0

    @property
    def template(self) -> str:
        return FLOWCHART_TEMPLATE

    def write_markdown(self) -> tuple[str, ...]:
        return ('```mermaid', *self.lines, '```')


@dataclass(slots=True, kw_only=True, frozen=True)
class CodeListing:
    language: str
    source: str
    count: int = 0

    @property
    def template(self) -> str:
        return LISTING_TEMPLATE

    def write_markdown(self) -> tuple[str, ...]:
        return (f'```{self.language}', *self.source.splitlines(), '```')


@dataclass(slots=True, kw_only=True, frozen=True)
class Section:
    title: str
    blocks: tuple[Block, ...] = ()
    kind: str | None = None
    note: str = ''
    folded: bool = False
    column: bool = False

    @property
    def count(self) -> int:
        return sum(block.count for block in self.blocks)


@dataclass(slots=True, kw_only=True, frozen=True)
class Fact:
    label: str
    value: Line
    wide: bool = False


@dataclass(slots=True, kw_only=True, frozen=True)
class Term:
    word: str
    meaning: str


@dataclass(slots=True, kw_only=True, frozen=True)
class Document:
    title: str
    summary: tuple[Line, ...] = ()
    facts: tuple[Fact, ...] = ()
    sections: tuple[Section, ...] = ()
    appendix: tuple[Section, ...] = ()
    terms: tuple[Term, ...] = ()


@runtime_checkable
class PageRenderer(Protocol):
    def render(self, document: Document) -> str: ...
