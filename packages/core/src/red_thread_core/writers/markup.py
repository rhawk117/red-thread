"""HTML from the document tree: every value escaped by one function, every node one fragment."""

from dataclasses import dataclass
from html import escape
from string.templatelib import Interpolation, Template, convert
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from red_thread_core.documents import (
        Block,
        Code,
        CodeListing,
        Fact,
        Inline,
        Line,
        Link,
        Section,
        Text,
    )


def render_value(value: object) -> str:
    if isinstance(value, Template):
        return render(value)
    if isinstance(value, tuple):
        return ''.join(map(render_value, value))
    return escape(str(value))


def render_part(part: str | Interpolation[object]) -> str:
    if isinstance(part, Interpolation):
        return render_value(convert(part.value, part.conversion))
    return part


def render(template: Template) -> str:
    return ''.join(map(render_part, template))


@dataclass(slots=True, kw_only=True, frozen=True)
class HtmlInlines:
    def write_text(self, node: Text) -> Template:
        return t'{node.value}'

    def write_code(self, node: Code) -> Template:
        return t'<code>{node.value}</code>'

    def write_link(self, node: Link) -> Template:
        return t'<a href="{node.url}" rel="noreferrer">{node.url}</a>'

    def write_inline(self, node: Inline) -> Template:
        return node.write(self)

    def write_line(self, line: Line) -> Template:
        return t'{tuple(map(self.write_inline, line))}'


def write_line(line: Line) -> Template:
    return HtmlInlines().write_line(line)


def write_ref(ref: str) -> Template:
    return t'<button type="button" class="ref" data-copy="{ref}" title="Copy">{ref}</button>'


def write_paragraph(line: Line) -> Template:
    return t'<p>{write_line(line)}</p>'


def write_point(point: Line) -> Template:
    claim = t'<p class="claim">{write_line(point)}</p>'
    return t'<li class="entry"><div>{claim}</div></li>'


def write_points(points: tuple[Line, ...]) -> Template:
    if not points:
        return t''
    return t'<ol class="plain">{tuple(map(write_point, points))}</ol>'


def write_flowchart(lines: tuple[str, ...]) -> Template:
    return t'<pre class="mermaid">{"\n".join(lines)}</pre>'


def write_listing(listing: CodeListing | None) -> Template:
    if listing is None:
        return t''
    code = t'<code>{listing.source}</code>'
    return t'<pre class="listing" data-language="{listing.language}">{code}</pre>'


def write_fold(section: Section, body: Template) -> Template:
    count = t'<span class="count">{section.count}</span>' if section.count else t''
    note = t'<span class="about">{section.note}</span>' if section.note else t''
    kind = t' data-kind="{section.kind}"' if section.kind is not None else t''
    state = t'' if section.folded else t' open'
    heading = t'<summary><h2>{section.title}</h2>{count}{note}</summary>'
    return t'<details class="section"{kind}{state}>\n{heading}\n{body}\n</details>\n'


def write_block(block: Block) -> Template:
    return block.write_html()


def write_section(section: Section) -> Template:
    return write_fold(section, t'{tuple(map(write_block, section.blocks))}')


def write_fact(fact: Fact) -> Template:
    style = 'fact wide' if fact.wide else 'fact'
    return t'<div class="{style}"><dt>{fact.label}</dt><dd>{write_line(fact.value)}</dd></div>'
