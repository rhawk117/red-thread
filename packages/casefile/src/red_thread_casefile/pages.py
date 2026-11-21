"""A board or a lens output as one page, styled by Tailwind and drawn by mermaid from cdnjs."""

import re
from collections import Counter
from dataclasses import dataclass
from html import escape
from itertools import chain, zip_longest
from string import Template as PageTemplate
from string.templatelib import Interpolation, Template, convert
from typing import TYPE_CHECKING, Literal

from red_thread_casefile.assets import read_asset
from red_thread_casefile.charts import MAIN_LEDGER
from red_thread_casefile.domain import Cite
from red_thread_casefile.views import SECTIONS

if TYPE_CHECKING:
    from red_thread_casefile.views import Document, Item, Section

type FilterName = Literal['kind', 'thread']

CODE_SPAN = re.compile(r'`([^`]+)`')
MIN_CHIPS = 2


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


def write_cite(cite: str | None) -> Template:
    if cite is None:
        return t''
    copy = t'<button type="button" class="copy" data-copy="{cite}">Copy</button>'
    if Cite(raw=cite).is_url:
        return t'<p class="cite"><a href="{cite}" rel="noreferrer">{cite}</a>{copy}</p>'
    return t'<p class="cite"><code>{cite}</code>{copy}</p>'


def write_ref(ref: str) -> Template:
    return t'<button type="button" class="ref" data-copy="{ref}" title="Copy">{ref}</button>'


def write_notes(item: Item) -> Template:
    flags = tuple(t'<li class="flag">{flag}</li>' for flag in item.flags)
    notes = tuple(t'<li>{note}</li>' for note in item.notes)
    if not flags and not notes:
        return t''
    return t'<ul class="notes">{flags}{notes}</ul>'


def write_diagram(diagram: str | None) -> Template:
    if diagram is None:
        return t''
    return t'<pre class="mermaid">{diagram}</pre>'


def write_item(item: Item) -> Template:
    claim = t'<p class="claim">{mark_up(item.text)}</p>'
    diagram = write_diagram(item.diagram)
    body = t'<div>{claim}{write_cite(item.cite)}{write_notes(item)}{diagram}</div>'
    if item.ref is None:
        return t'<li class="entry">{body}</li>'
    kind = item.kind or ''
    thread = item.thread or ''
    marks = t'data-kind="{kind}" data-thread="{thread}"'
    return t'<li class="entry" {marks}>{write_ref(item.ref)}{body}</li>'


def write_listing(section: Section) -> Template:
    if not section.items:
        return t''
    threaded = any(item.ref is not None for item in section.items)
    style = 'thread' if threaded else 'plain'
    items = tuple(map(write_item, section.items))
    return t'<ol class="{style}">{items}</ol>'


def write_fold(title: str, body: Template) -> Template:
    heading = t'<summary><h2>{title}</h2></summary>'
    return t'<details class="section" open>\n{heading}\n{body}\n</details>\n'


def write_section(section: Section) -> Template:
    prose = tuple(t'<p>{mark_up(line)}</p>' for line in section.prose)
    return write_fold(section.title, t'{prose}{write_listing(section)}')


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
            Chip(group='kind', value=kind, label=title, count=counted[kind])
            for kind, title in SECTIONS
            if counted[kind]
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
        return write_fold('Map', t'<pre class="mermaid">{source}</pre>')

    def render(self) -> str:
        summary = tuple(t'<li>{mark_up(line)}</li>' for line in self.document.summary)
        sections = tuple(map(write_section, self.document.sections))
        return PageTemplate(read_asset('page.html')).substitute(
            title=escape(self.document.title),
            style=read_asset('page.css'),
            theme=read_asset('tailwind.css'),
            script=read_asset('page.js'),
            summary=render(t'{summary}'),
            toolbar=render(self.write_toolbar()),
            sections=render(t'{sections}{self.write_map()}'),
        )
