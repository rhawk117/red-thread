"""A document as one page: a rail of what the page is, beside its sections in columns."""

from dataclasses import dataclass
from itertools import groupby
from operator import attrgetter
from string import Template as PageTemplate
from typing import TYPE_CHECKING

from red_thread_core.packaged import read_asset
from red_thread_core.writers.markup import (
    anchor_section,
    render,
    write_fact,
    write_line,
    write_section,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from string.templatelib import Template

    from red_thread_core.documents import Document, Section, Term

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


def write_chip(chip: Chip) -> Template:
    state = t'data-filter="{chip.group}" data-value="{chip.value}" aria-pressed="true"'
    count = t'<span class="count">{chip.count}</span>'
    return t'<button type="button" class="chip" {state}>{chip.label} {count}</button>'


def write_chips(chips: ChipRow) -> Template:
    if len(chips) < MIN_CHIPS:
        return t''
    label = f'Filter by {chips[0].group}'
    buttons = tuple(map(write_chip, chips))
    return t'<div class="chips" role="group" aria-label="{label}">{buttons}</div>'


def write_group(group: tuple[bool, Iterable[Section]]) -> Template:
    column, sections = group
    written = tuple(map(write_section, sections))
    if not column:
        return t'{written}'
    return t'<div class="columns">\n{written}</div>\n'


def write_sections(sections: tuple[Section, ...]) -> Template:
    groups = groupby(sections, key=attrgetter('column'))
    return t'{tuple(map(write_group, groups))}'


def write_content_link(section: Section) -> Template:
    return t'<li><a href="#{anchor_section(section.title)}">{section.title}</a></li>'


def write_term(term: Term) -> Template:
    return t'<div><dt>{term.word}</dt><dd>{term.meaning}</dd></div>'


@dataclass(slots=True, kw_only=True, frozen=True)
class HtmlPage:
    document: Document
    filters: tuple[ChipRow, ...] = ()

    @property
    def sections(self) -> tuple[Section, ...]:
        return (*self.document.sections, *self.document.appendix)

    def write_toolbar(self) -> Template:
        if not self.document.sections:
            return t''
        chips = tuple(map(write_chips, self.filters))
        fold = t'<button type="button" class="tool" data-fold>Collapse all</button>'
        return t'<nav class="toolbar" aria-label="Page controls">{chips}{fold}</nav>\n'

    def write_contents(self) -> Template:
        if len(self.sections) < MIN_CONTENTS:
            return t''
        links = tuple(map(write_content_link, self.sections))
        return t'<nav class="contents" aria-label="Sections"><ol>{links}</ol></nav>\n'

    def write_terms(self) -> Template:
        if not self.document.terms:
            return t''
        terms = tuple(map(write_term, self.document.terms))
        heading = t'<summary>{TERMS_TITLE}</summary>'
        return t'<details class="terms">{heading}<dl>{terms}</dl></details>\n'

    def write_summary(self) -> Template:
        lines = tuple(t'<li>{write_line(line)}</li>' for line in self.document.summary)
        meta = t'<ul class="meta">{lines}</ul>\n' if lines else t''
        facts = tuple(map(write_fact, self.document.facts))
        listed = t'<dl class="facts">{facts}</dl>\n' if facts else t''
        return t'{meta}{listed}'

    def render(self) -> str:
        return PageTemplate(read_asset('page.html')).substitute(
            title=render(t'{self.document.title}'),
            style=read_asset('page.css'),
            theme=read_asset('tailwind.css'),
            script=read_asset('page.js'),
            summary=render(self.write_summary()),
            toolbar=render(self.write_toolbar()),
            contents=render(self.write_contents()),
            terms=render(self.write_terms()),
            sections=render(write_sections(self.sections)),
        )
