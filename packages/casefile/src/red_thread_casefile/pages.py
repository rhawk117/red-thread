"""A board or a lens output as one page, styled by Tailwind and drawn by mermaid from cdnjs."""

import re
from collections import Counter
from dataclasses import dataclass
from html import escape
from itertools import chain, zip_longest
from string import Template as PageTemplate
from typing import TYPE_CHECKING, Literal

from red_thread_casefile.assets import read_asset
from red_thread_casefile.charts import MAIN_LEDGER
from red_thread_casefile.domain import Cite, date_of
from red_thread_casefile.views import HEADINGS, Section
from red_thread_casefile.writers.markup import render

if TYPE_CHECKING:
    from string.templatelib import Template

    from red_thread_casefile.policy import Finding
    from red_thread_casefile.views import Document, Fact, Item

type FilterName = Literal['kind', 'thread']

CODE_SPAN = re.compile(r'`([^`]+)`')
MIN_CHIPS = 2
STATE_TITLE = 'The citation at the last check'
MAP_NOTE = (
    'Each thread as a line of its entries, with an arrow from an entry to the one it retired.'
)
RETIRED_NOTE = (
    'Entries a later entry replaced. The ledger keeps them and the sections leave them out.'
)


def mark_up(text: str) -> tuple[Template, ...]:
    pieces = CODE_SPAN.split(text)
    plain = (t'{piece}' for piece in pieces[::2])
    code = (t'<code>{piece}</code>' for piece in pieces[1::2])
    return tuple(chain.from_iterable(zip_longest(plain, code, fillvalue=t'')))


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


def write_value(value: str) -> Template:
    if Cite(raw=value).is_url:
        return t'<a href="{value}" rel="noreferrer">{value}</a>'
    return t'{mark_up(value)}'


def write_fact(fact: Fact) -> Template:
    style = 'fact wide' if fact.wide else 'fact'
    return t'<div class="{style}"><dt>{fact.label}</dt><dd>{write_value(fact.value)}</dd></div>'


def write_facts(facts: tuple[Fact, ...]) -> Template:
    if not facts:
        return t''
    return t'<dl class="facts">{tuple(map(write_fact, facts))}</dl>\n'


def label_state(finding: Finding) -> str:
    if finding.state != 'moved' or finding.moved_to is None:
        return finding.state
    return f'moved to line {finding.moved_to}'


def write_state(finding: Finding | None) -> Template:
    if not finding:
        return t''
    marks = t'class="state" data-state="{finding.state}" title="{STATE_TITLE}"'
    return t'<span {marks}>{label_state(finding)}</span>'


def write_cite(item: Item) -> Template:
    if item.cite is None:
        return t''
    copy = t'<button type="button" class="copy" data-copy="{item.cite}">Copy</button>'
    tools = t'{write_state(item.finding)}{copy}'
    if Cite(raw=item.cite).is_url:
        return t'<p class="cite"><a href="{item.cite}" rel="noreferrer">{item.cite}</a>{tools}</p>'
    quote = t'<pre class="quote"><code>{item.quote}</code></pre>' if item.quote is not None else t''
    return t'<p class="cite"><code>{item.cite}</code>{tools}</p>{quote}'


def write_ref(ref: str) -> Template:
    return t'<button type="button" class="ref" data-copy="{ref}" title="Copy">{ref}</button>'


def write_stamps(item: Item) -> tuple[Template, ...]:
    rounds = (t'<li class="stamp">round {item.round}</li>',) if item.round is not None else ()
    if item.at is None:
        return rounds
    day = date_of(item.at)
    return (*rounds, t'<li class="stamp"><time datetime="{item.at}">{day}</time></li>')


def write_notes(item: Item) -> Template:
    flags = tuple(t'<li class="flag">{flag}</li>' for flag in item.flags)
    notes = tuple(t'<li>{note}</li>' for note in item.notes)
    marks = (*write_stamps(item), *flags, *notes)
    if not marks:
        return t''
    return t'<ul class="notes">{marks}</ul>'


def write_claim(item: Item) -> Template:
    if not item.verdict:
        return t'<p class="claim">{mark_up(item.text)}</p>'
    badge = t'<span class="verdict" data-verdict="{item.verdict}">{item.verdict}</span>'
    return t'<p class="claim">{badge} {mark_up(item.text)}</p>'


def write_diagram(diagram: str | None) -> Template:
    if diagram is None:
        return t''
    return t'<pre class="mermaid">{diagram}</pre>'


def write_item(item: Item) -> Template:
    diagram = write_diagram(item.diagram)
    body = t'<div>{write_claim(item)}{write_cite(item)}{write_notes(item)}{diagram}</div>'
    if item.ref is None:
        return t'<li class="entry">{body}</li>'
    kind = item.kind or ''
    thread = item.thread or ''
    marks = t'data-kind="{kind}" data-thread="{thread}"'
    return t'<li class="entry" {marks}>{write_ref(item.ref)}{body}</li>'


def is_threaded(section: Section) -> bool:
    return any(item.ref is not None for item in section.items)


def write_listing(section: Section) -> Template:
    if not section.items:
        return t''
    style = 'thread' if is_threaded(section) else 'plain'
    items = tuple(map(write_item, section.items))
    return t'<ol class="{style}">{items}</ol>'


def write_fold(section: Section, body: Template) -> Template:
    count = t'<span class="count">{len(section.items)}</span>' if is_threaded(section) else t''
    note = t'<span class="about">{section.note}</span>' if section.note else t''
    kind = t' data-kind="{section.kind}"' if section.kind else t''
    state = t'' if section.folded else t' open'
    heading = t'<summary><h2>{section.title}</h2>{count}{note}</summary>'
    return t'<details class="section"{kind}{state}>\n{heading}\n{body}\n</details>\n'


def write_section(section: Section) -> Template:
    prose = tuple(t'<p>{mark_up(line)}</p>' for line in section.prose)
    return write_fold(section, t'{prose}{write_listing(section)}')


@dataclass(slots=True, kw_only=True, frozen=True)
class HtmlWriter:
    document: Document

    @property
    def entries(self) -> tuple[Item, ...]:
        items = chain.from_iterable(section.items for section in self.document.sections)
        return tuple(item for item in items if item.ref is not None)

    def list_kind_chips(self) -> list[Chip]:
        counted = Counter(item.kind for item in self.entries)
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
        counted = Counter(item.thread or '' for item in self.entries)
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

    def write_map(self) -> Template:
        if not self.document.map_lines:
            return t''
        source = '\n'.join((read_asset('map.mmd').rstrip(), *self.document.map_lines))
        return write_fold(
            Section(title='Map', note=MAP_NOTE), t'<pre class="mermaid">{source}</pre>'
        )

    def write_retired(self) -> Template:
        if not self.document.retired:
            return t''
        retired = self.document.retired
        return write_section(
            Section(title='Retired', items=retired, note=RETIRED_NOTE, folded=True)
        )

    def write_summary(self) -> Template:
        lines = tuple(t'<li>{mark_up(line)}</li>' for line in self.document.summary)
        meta = t'<ul class="meta">{lines}</ul>\n' if lines else t''
        return t'{meta}{write_facts(self.document.facts)}'

    def render(self) -> str:
        sections = tuple(map(write_section, self.document.sections))
        return PageTemplate(read_asset('page.html')).substitute(
            title=escape(self.document.title),
            style=read_asset('page.css'),
            theme=read_asset('tailwind.css'),
            script=read_asset('page.js'),
            summary=render(self.write_summary()),
            toolbar=render(self.write_toolbar()),
            sections=render(t'{sections}{self.write_map()}{self.write_retired()}'),
        )
