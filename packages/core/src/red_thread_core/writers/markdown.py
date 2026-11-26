"""Markdown from the document tree: what an output writes to a .md file."""

from dataclasses import dataclass
from itertools import chain
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from red_thread_core.documents import Block, Code, Document, Inline, Line, Link, Section, Text


@dataclass(slots=True, kw_only=True, frozen=True)
class MarkdownInlines:
    def write_text(self, node: Text) -> str:
        return node.value

    def write_code(self, node: Code) -> str:
        return f'`{node.value}`'

    def write_link(self, node: Link) -> str:
        return node.url

    def write_inline(self, node: Inline) -> str:
        return node.write(self)

    def write_line(self, line: Line) -> str:
        return ''.join(map(self.write_inline, line))


def write_markdown_line(line: Line) -> str:
    return MarkdownInlines().write_line(line)


def write_block(block: Block) -> tuple[str, ...]:
    return block.write_markdown()


def write_section(section: Section) -> tuple[str, ...]:
    blocks = chain.from_iterable(map(write_block, section.blocks))
    return ('', f'## {section.title}', '', *blocks)


@dataclass(slots=True, kw_only=True, frozen=True)
class MarkdownWriter:
    document: Document

    def render(self) -> str:
        document = self.document
        summary = map(write_markdown_line, document.summary)
        sections = (*document.sections, *document.appendix)
        written = chain.from_iterable(map(write_section, sections))
        lines = (f'# {document.title}', '', *summary, *written)
        return '\n'.join(lines) + '\n'
