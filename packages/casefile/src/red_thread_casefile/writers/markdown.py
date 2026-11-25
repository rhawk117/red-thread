"""Markdown from the document tree: what a lens writes to out/<lens>.md."""

from dataclasses import dataclass, field
from itertools import chain
from typing import TYPE_CHECKING

from red_thread_casefile.views import list_cite_flags

if TYPE_CHECKING:
    from red_thread_casefile.documents import (
        Block,
        Citation,
        Code,
        Document,
        EntryList,
        EntryNode,
        Flowchart,
        Inline,
        Line,
        Link,
        Paragraph,
        PointList,
        Section,
        Text,
    )

type Lines = tuple[str, ...]


def write_citation(citation: Citation | None) -> str:
    if citation is None:
        return ''

    if citation.is_url:
        return f' <{citation.target}>'

    return f' `{citation.target}`'


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


@dataclass(slots=True, kw_only=True, frozen=True)
class MarkdownWriter:
    document: Document
    inlines: MarkdownInlines = field(default_factory=MarkdownInlines)

    def write_entry(self, entry: EntryNode) -> str:
        finding = entry.citation.finding if entry.citation else None
        notes = (note.text for note in entry.notes)
        remarks = '; '.join((*entry.flags, *list_cite_flags(finding), *notes))
        noted = f' ({remarks})' if remarks else ''
        cite = write_citation(entry.citation)
        return f'- {self.inlines.write_line(entry.claim)}{noted}{cite} [{entry.ref}]'

    def write_paragraph(self, node: Paragraph) -> Lines:
        return (self.inlines.write_line(node.line),)

    def write_entries(self, node: EntryList) -> Lines:
        return tuple(map(self.write_entry, node.entries))

    def write_points(self, node: PointList) -> Lines:
        return tuple(f'- {self.inlines.write_line(point)}' for point in node.points)

    def write_flowchart(self, node: Flowchart) -> Lines:
        return ('```mermaid', *node.lines, '```')

    def write_block(self, block: Block) -> Lines:
        return block.write(self)

    def write_section(self, section: Section) -> Lines:
        blocks = chain.from_iterable(map(self.write_block, section.blocks))
        return ('', f'## {section.title}', '', *blocks)

    def render(self) -> str:
        document = self.document
        summary = map(self.inlines.write_line, document.summary)
        sections = (*document.sections, *document.appendix)
        written = chain.from_iterable(map(self.write_section, sections))
        lines = (f'# {document.title}', '', *summary, *written)
        return '\n'.join(lines) + '\n'
