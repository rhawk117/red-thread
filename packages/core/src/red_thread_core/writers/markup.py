"""HTML from the document tree: every node one element, built with the element builder."""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_core.elements import element

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
    from red_thread_core.elements import Element, Node

NOT_ANCHOR = re.compile(r'[^a-z0-9]+')


@dataclass(slots=True, kw_only=True, frozen=True)
class HtmlInlines:
    def write_text(self, node: Text) -> Node:
        return node.value

    def write_code(self, node: Code) -> Node:
        return element('code').set_text(node.value)

    def write_link(self, node: Link) -> Node:
        return element('a').attributes({'href': node.url, 'rel': 'noreferrer'}).set_text(node.shown)

    def write_inline(self, node: Inline) -> Node:
        return node.write(self)

    def write_line(self, line: Line) -> tuple[Node, ...]:
        return tuple(map(self.write_inline, line))


def write_line(line: Line) -> tuple[Node, ...]:
    return HtmlInlines().write_line(line)


def write_ref(ref: str) -> Element:
    marks = {'type': 'button', 'class': 'ref', 'data-copy': ref, 'title': 'Copy'}
    return element('button').attributes(marks).set_text(ref)


def write_paragraph(line: Line) -> Element:
    return element('p').nest(*write_line(line))


def write_point(point: Line) -> Element:
    claim = element('p').attributes({'class': 'claim'}).nest(*write_line(point))
    return element('li').attributes({'class': 'entry'}).nest(element('div').nest(claim))


def write_points(points: tuple[Line, ...]) -> Element | None:
    if not points:
        return None
    return element('ol').attributes({'class': 'plain'}).nest(*map(write_point, points))


def write_flowchart(lines: tuple[str, ...]) -> Element:
    return element('pre').attributes({'class': 'mermaid'}).set_text('\n'.join(lines))


def write_listing(listing: CodeListing) -> Element:
    code = element('code').set_text(listing.source)
    marks = {'class': 'listing', 'data-language': listing.language}
    return element('pre').attributes(marks).nest(code)


def anchor_section(title: str) -> str:
    return 'section-' + NOT_ANCHOR.sub('-', title.lower()).strip('-')


def write_heading(section: Section) -> Element:
    count = element('span').attributes({'class': 'count'}).set_text(section.count)
    note = element('span').attributes({'class': 'about'}).set_text(section.note)
    return element('summary').nest(
        element('h2').set_text(section.title),
        count if section.count else None,
        note if section.note else None,
    )


def write_block(block: Block) -> Element | None:
    return block.write_html()


def write_section(section: Section) -> Element:
    marks = {
        'class': 'section',
        'id': anchor_section(section.title),
        'data-kind': section.kind,
        'open': not section.folded,
    }
    blocks = map(write_block, section.blocks)
    return element('details').attributes(marks).nest(write_heading(section), *blocks)


def write_fact(fact: Fact) -> Element:
    style = 'fact wide' if fact.wide else 'fact'
    return (
        element('div')
        .attributes({'class': style})
        .nest(element('dt').set_text(fact.label), element('dd').nest(*write_line(fact.value)))
    )
