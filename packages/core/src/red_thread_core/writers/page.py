"""A document as one page: a rail of what the page is, beside its sections in columns."""

from dataclasses import dataclass
from html import escape
from itertools import chain, groupby
from operator import attrgetter
from string import Template as PageTemplate
from typing import TYPE_CHECKING

from red_thread_core.elements import element, render_fragment
from red_thread_core.packaged import read_asset
from red_thread_core.writers.markup import (
    anchor_section,
    write_fact,
    write_line,
    write_section,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from red_thread_core.documents import Document, Line, Section, Term
    from red_thread_core.elements import Element

MIN_CHIPS = 2
MIN_CONTENTS = 2
TERMS_TITLE = 'What the words on this page mean'


@dataclass(slots=True, kw_only=True, frozen=True)
class Chip:
    group: str
    value: str
    label: str
    count: int


type ChipRow = tuple[Chip, ...]


def write_chip(chip: Chip) -> Element:
    marks = {
        'type': 'button',
        'class': 'chip',
        'data-filter': chip.group,
        'data-value': chip.value,
        'aria-pressed': 'true',
    }
    count = element('span').attributes({'class': 'count'}).set_text(chip.count)
    return element('button').attributes(marks).nest(f'{chip.label} ', count)


def write_chips(chips: ChipRow) -> Element | None:
    if len(chips) < MIN_CHIPS:
        return None
    marks = {'class': 'chips', 'role': 'group', 'aria-label': f'Filter by {chips[0].group}'}
    return element('div').attributes(marks).nest(*map(write_chip, chips))


def write_group(group: tuple[bool, Iterable[Section]]) -> tuple[Element, ...]:
    column, sections = group
    written = tuple(map(write_section, sections))
    if not column:
        return written
    return (element('div').attributes({'class': 'columns'}).nest(*written),)


def write_sections(sections: tuple[Section, ...]) -> tuple[Element, ...]:
    groups = groupby(sections, key=attrgetter('column'))
    return tuple(chain.from_iterable(map(write_group, groups)))


def write_content_link(section: Section) -> Element:
    link = element('a').attributes({'href': f'#{anchor_section(section.title)}'})
    return element('li').nest(link.set_text(section.title))


def write_term(term: Term) -> Element:
    return element('div').nest(
        element('dt').set_text(term.word), element('dd').set_text(term.meaning)
    )


def write_summary_line(line: Line) -> Element:
    return element('li').nest(*write_line(line))


@dataclass(slots=True, kw_only=True, frozen=True)
class HtmlPage:
    document: Document
    filters: tuple[ChipRow, ...] = ()

    @property
    def sections(self) -> tuple[Section, ...]:
        return (*self.document.sections, *self.document.appendix)

    def write_toolbar(self) -> Element | None:
        if not self.document.sections:
            return None
        fold = element('button').attributes({'type': 'button', 'class': 'tool', 'data-fold': True})
        marks = {'class': 'toolbar', 'aria-label': 'Page controls'}
        chips = map(write_chips, self.filters)
        return element('nav').attributes(marks).nest(*chips, fold.set_text('Collapse all'))

    def write_contents(self) -> Element | None:
        if len(self.sections) < MIN_CONTENTS:
            return None
        links = element('ol').nest(*map(write_content_link, self.sections))
        return (
            element('nav').attributes({'class': 'contents', 'aria-label': 'Sections'}).nest(links)
        )

    def write_terms(self) -> Element | None:
        if not self.document.terms:
            return None
        terms = element('dl').nest(*map(write_term, self.document.terms))
        heading = element('summary').set_text(TERMS_TITLE)
        return element('details').attributes({'class': 'terms'}).nest(heading, terms)

    def write_meta(self) -> Element | None:
        if not self.document.summary:
            return None
        lines = map(write_summary_line, self.document.summary)
        return element('ul').attributes({'class': 'meta'}).nest(*lines)

    def write_facts(self) -> Element | None:
        if not self.document.facts:
            return None
        facts = map(write_fact, self.document.facts)
        return element('dl').attributes({'class': 'facts'}).nest(*facts)

    def render(self) -> str:
        return PageTemplate(read_asset('page.html')).substitute(
            title=escape(self.document.title),
            style=read_asset('page.css'),
            theme=read_asset('tailwind.css'),
            script=read_asset('page.js'),
            summary=render_fragment((self.write_meta(), self.write_facts())),
            toolbar=render_fragment((self.write_toolbar(),)),
            contents=render_fragment((self.write_contents(),)),
            terms=render_fragment((self.write_terms(),)),
            sections=render_fragment(write_sections(self.sections)),
        )
