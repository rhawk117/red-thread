"""HtmlPage: the toolbar's chips, the header's summary and facts, and the order of the panels."""

from dataclasses import replace
from typing import TYPE_CHECKING

from red_thread_casefile.documents import EntryList
from red_thread_core.documents import Document, Section, parse_line

from tests.casefile.pages.html_reading import (
    join_layout,
    list_chip_groups,
    list_section_titles,
)
from tests.casefile.writers.builders import create_entry_node
from tests.casefile.writers.reading import render_page

if TYPE_CHECKING:
    from red_thread_casefile.documents import EntryNode


def create_threaded_entry(ref: str) -> EntryNode:
    thread = 'T1' if '.' in ref else None
    return replace(create_entry_node(f'claim {ref}', ref), thread=thread)


def create_section(title: str, *refs: str) -> Section:
    entries = tuple(map(create_threaded_entry, refs))
    return Section(title=title, blocks=(EntryList(entries=entries),), kind='known')


class TestToolbar:
    def test_chips_count_the_entries_of_the_sections_and_not_of_the_appendix(self) -> None:
        document = Document(
            title='t',
            sections=(create_section('Known', 'e1', 'T1.e1'),),
            appendix=(replace(create_section('Retired', 'e2', 'e3'), kind=None),),
        )

        groups = list_chip_groups(render_page(document))

        threads = [(chip.label, chip.count) for chip in groups[0]]
        assert threads == [('main ledger', 1), ('T1', 1)]

    def test_a_page_without_sections_has_no_toolbar(self) -> None:
        page = render_page(Document(title='t', appendix=(create_section('Retired', 'e2'),)))

        assert 'class="toolbar"' not in page


class TestLayout:
    def test_the_appendix_follows_the_sections(self) -> None:
        document = Document(
            title='t',
            sections=(create_section('Known', 'e1'),),
            appendix=(create_section('Map'), create_section('Retired', 'e9')),
        )

        assert list_section_titles(render_page(document)) == ['Known', 'Map', 'Retired']

    def test_the_summary_is_a_list_of_lines_with_code_spans(self) -> None:
        page = render_page(Document(title='t', summary=(parse_line('Case `c1`'),)))

        assert '<ul class="meta"><li>Case <code>c1</code></li></ul>' in join_layout(page)
