"""A document as one page, styled by Tailwind and drawn by mermaid from cdnjs."""

from dataclasses import dataclass
from string import Template as PageTemplate
from typing import TYPE_CHECKING

from red_thread_core.assets import read_asset
from red_thread_core.writers.markup import render, write_fact, write_line, write_section

if TYPE_CHECKING:
    from string.templatelib import Template

    from red_thread_core.documents import Document

MIN_CHIPS = 2


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


@dataclass(slots=True, kw_only=True, frozen=True)
class HtmlPage:
    document: Document
    filters: tuple[ChipRow, ...] = ()

    def write_toolbar(self) -> Template:
        if not self.document.sections:
            return t''
        chips = tuple(map(write_chips, self.filters))
        fold = t'<button type="button" class="tool" data-fold>Collapse all</button>'
        return t'<nav class="toolbar" aria-label="Page controls">{chips}{fold}</nav>\n'

    def write_summary(self) -> Template:
        lines = tuple(t'<li>{write_line(line)}</li>' for line in self.document.summary)
        meta = t'<ul class="meta">{lines}</ul>\n' if lines else t''
        facts = tuple(map(write_fact, self.document.facts))
        listed = t'<dl class="facts">{facts}</dl>\n' if facts else t''
        return t'{meta}{listed}'

    def render(self) -> str:
        document = self.document
        sections = (*document.sections, *document.appendix)
        written = tuple(map(write_section, sections))
        return PageTemplate(read_asset('page.html')).substitute(
            title=render(t'{document.title}'),
            style=read_asset('page.css'),
            theme=read_asset('tailwind.css'),
            script=read_asset('page.js'),
            summary=render(self.write_summary()),
            toolbar=render(self.write_toolbar()),
            sections=render(t'{written}'),
        )
