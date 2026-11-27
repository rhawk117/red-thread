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
    from red_thread_core.elements import Element, ElementChild

NON_ANCHOR_CHARACTERS = re.compile(r'[^a-z0-9]+')


@dataclass(slots=True, kw_only=True, frozen=True)
class HtmlInlines:
    def write_text(self, node: Text) -> ElementChild:
        return node.value

    def write_code(self, node: Code) -> ElementChild:
        return element('code').set_text(node.value)

    def write_link(self, node: Link) -> ElementChild:
        return (
            element('a')
            .with_attributes({'href': node.url, 'rel': 'noreferrer'})
            .set_text(node.link_text)
        )

    def write_inline(self, node: Inline) -> ElementChild:
        return node.write(self)

    def write_line(self, line: Line) -> tuple[ElementChild, ...]:
        return tuple(map(self.write_inline, line))


def write_line(line: Line) -> tuple[ElementChild, ...]:
    return HtmlInlines().write_line(line)


def write_finding_id_button(finding_id: str) -> Element:
    attributes = {'type': 'button', 'class': 'finding-id', 'data-copy': finding_id, 'title': 'Copy'}
    return element('button').with_attributes(attributes).set_text(finding_id)


def write_paragraph(line: Line) -> Element:
    return element('p').nest(*write_line(line))


def write_point(point: Line) -> Element:
    claim = element('p').with_attributes({'class': 'claim'}).nest(*write_line(point))
    return element('li').with_attributes({'class': 'finding'}).nest(element('div').nest(claim))


def write_point_list(points: tuple[Line, ...]) -> Element | None:
    if not points:
        return None
    return element('ol').with_attributes({'class': 'plain'}).nest(*map(write_point, points))


def write_flowchart(lines: tuple[str, ...]) -> Element:
    return element('pre').with_attributes({'class': 'mermaid'}).set_text('\n'.join(lines))


def write_code_listing(listing: CodeListing) -> Element:
    code = element('code').set_text(listing.source)
    attributes = {'class': 'listing', 'data-language': listing.language}
    return element('pre').with_attributes(attributes).nest(code)


def name_section_anchor(title: str) -> str:
    return 'section-' + NON_ANCHOR_CHARACTERS.sub('-', title.lower()).strip('-')


def write_section_summary(section: Section) -> Element:
    count = element('span').with_attributes({'class': 'count'}).set_text(section.count)
    note = element('span').with_attributes({'class': 'about'}).set_text(section.note)
    return element('summary').nest(
        element('h2').set_text(section.title),
        count if section.count else None,
        note if section.note else None,
    )


def write_block(block: Block) -> Element | None:
    return block.write_html()


def write_section(section: Section) -> Element:
    attributes = {
        'class': 'section',
        'id': name_section_anchor(section.title),
        'data-kind': section.kind,
        'open': not section.folded,
    }
    blocks = map(write_block, section.blocks)
    return (
        element('details').with_attributes(attributes).nest(write_section_summary(section), *blocks)
    )


def write_fact(fact: Fact) -> Element:
    style = 'fact wide' if fact.wide else 'fact'
    return (
        element('div')
        .with_attributes({'class': style})
        .nest(element('dt').set_text(fact.label), element('dd').nest(*write_line(fact.value)))
    )
