"""A board or a lens output as one page, styled by Tailwind and drawn by mermaid from cdnjs."""

from collections import Counter
from dataclasses import dataclass, field
from string import Template as PageTemplate
from typing import TYPE_CHECKING, Literal

from red_thread_casefile.assets import read_asset
from red_thread_casefile.charts import MAIN_LEDGER
from red_thread_casefile.views import HEADINGS
from red_thread_casefile.writers.markup import HtmlWriter, render

if TYPE_CHECKING:
    from string.templatelib import Template

    from red_thread_casefile.documents import Document, EntryNode

type FilterName = Literal['kind', 'thread']

MIN_CHIPS = 2


def order_name(name: str) -> tuple[int, str]:
    return (len(name), name)


@dataclass(slots=True, kw_only=True, frozen=True)
class Chip:
    group: FilterName
    value: str
    label: str
    count: int


def write_chip(chip: Chip) -> Template:
    state = t'data-filter="{chip.group}" data-value="{chip.value}" aria-pressed="true"'
    count = t'<span class="count">{chip.count}</span>'
    return t'<button type="button" class="chip" {state}>{chip.label} {count}</button>'


def write_chips(chips: list[Chip]) -> Template:
    if len(chips) < MIN_CHIPS:
        return t''
    label = f'Filter by {chips[0].group}'
    buttons = tuple(map(write_chip, chips))
    return t'<div class="chips" role="group" aria-label="{label}">{buttons}</div>'


def name_thread(entry: EntryNode) -> str:
    return entry.thread or ''


@dataclass(slots=True, kw_only=True, frozen=True)
class HtmlPage:
    document: Document
    writer: HtmlWriter = field(default_factory=HtmlWriter)

    def list_kind_chips(self) -> list[Chip]:
        counted = Counter(entry.kind for entry in self.document.entries)
        return [
            Chip(
                group='kind',
                value=heading.kind,
                label=heading.title,
                count=counted[heading.kind],
            )
            for heading in HEADINGS
            if counted[heading.kind]
        ]

    def list_thread_chips(self) -> list[Chip]:
        counted = Counter(map(name_thread, self.document.entries))
        return [
            Chip(group='thread', value=name, label=name or MAIN_LEDGER, count=counted[name])
            for name in sorted(counted, key=order_name)
        ]

    def write_toolbar(self) -> Template:
        if not self.document.sections:
            return t''
        kinds = write_chips(self.list_kind_chips())
        threads = write_chips(self.list_thread_chips())
        fold = t'<button type="button" class="tool" data-fold>Collapse all</button>'
        return t'<nav class="toolbar" aria-label="Page controls">{kinds}{threads}{fold}</nav>\n'

    def write_summary(self) -> Template:
        inlines = self.writer.inlines
        lines = tuple(t'<li>{inlines.write_line(line)}</li>' for line in self.document.summary)
        meta = t'<ul class="meta">{lines}</ul>\n' if lines else t''
        facts = tuple(map(self.writer.write_fact, self.document.facts))
        listed = t'<dl class="facts">{facts}</dl>\n' if facts else t''
        return t'{meta}{listed}'

    def render(self) -> str:
        document = self.document
        sections = (*document.sections, *document.appendix)
        written = tuple(map(self.writer.write_section, sections))
        return PageTemplate(read_asset('page.html')).substitute(
            title=render(t'{document.title}'),
            style=read_asset('page.css'),
            theme=read_asset('tailwind.css'),
            script=read_asset('page.js'),
            summary=render(self.write_summary()),
            toolbar=render(self.write_toolbar()),
            sections=render(t'{written}'),
        )
