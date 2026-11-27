"""The document tree that pages and Markdown are written from, open to blocks of any package."""

import re
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from red_thread_core.dto import DTO
from red_thread_core.writers.markdown import write_markdown_line
from red_thread_core.writers.markup import (
    write_code_listing,
    write_flowchart,
    write_paragraph,
    write_point_list,
)

if TYPE_CHECKING:
    from red_thread_core.elements import Element

CODE_SPAN = re.compile(r'`([^`]+)`')
URL_SCHEMES = ('http://', 'https://')


@runtime_checkable
class InlineWriter[T](Protocol):
    def write_text(self, node: Text) -> T: ...

    def write_code(self, node: Code) -> T: ...

    def write_link(self, node: Link) -> T: ...


@runtime_checkable
class Block(Protocol):
    @property
    def count(self) -> int: ...

    def write_html(self) -> Element | None: ...

    def write_markdown(self) -> tuple[str, ...]: ...


class Text(DTO, frozen=True, kw_only=True, gc=False):
    value: str

    def write[T](self, writer: InlineWriter[T]) -> T:
        return writer.write_text(self)


class Code(DTO, frozen=True, kw_only=True, gc=False):
    value: str

    def write[T](self, writer: InlineWriter[T]) -> T:
        return writer.write_code(self)


class Link(DTO, frozen=True, kw_only=True, gc=False):
    url: str
    label: str = ''

    @property
    def link_text(self) -> str:
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


class Paragraph(DTO, frozen=True, kw_only=True, gc=False):
    line: Line
    count: int = 0

    def write_html(self) -> Element | None:
        return write_paragraph(self.line)

    def write_markdown(self) -> tuple[str, ...]:
        return (write_markdown_line(self.line),)


class PointList(DTO, frozen=True, kw_only=True, gc=False):
    points: tuple[Line, ...]
    count: int = 0

    def write_html(self) -> Element | None:
        return write_point_list(self.points)

    def write_markdown(self) -> tuple[str, ...]:
        return tuple(f'- {write_markdown_line(point)}' for point in self.points)


class Flowchart(DTO, frozen=True, kw_only=True, gc=False):
    lines: tuple[str, ...]
    count: int = 0

    def write_html(self) -> Element | None:
        return write_flowchart(self.lines)

    def write_markdown(self) -> tuple[str, ...]:
        return ('```mermaid', *self.lines, '```')


class CodeListing(DTO, frozen=True, kw_only=True, gc=False):
    language: str
    source: str
    count: int = 0

    def write_html(self) -> Element | None:
        return write_code_listing(self)

    def write_markdown(self) -> tuple[str, ...]:
        return (f'```{self.language}', *self.source.splitlines(), '```')


class Section(DTO, frozen=True, kw_only=True, gc=False):
    title: str
    blocks: tuple[Block, ...] = ()
    kind: str | None = None
    note: str = ''
    folded: bool = False
    column: bool = False

    @property
    def count(self) -> int:
        return sum(block.count for block in self.blocks)


class Fact(DTO, frozen=True, kw_only=True, gc=False):
    label: str
    value: Line
    wide: bool = False


class Term(DTO, frozen=True, kw_only=True, gc=False):
    word: str
    meaning: str


class Document(DTO, frozen=True, kw_only=True, gc=False):
    title: str
    summary: tuple[Line, ...] = ()
    facts: tuple[Fact, ...] = ()
    sections: tuple[Section, ...] = ()
    appendix: tuple[Section, ...] = ()
    terms: tuple[Term, ...] = ()
