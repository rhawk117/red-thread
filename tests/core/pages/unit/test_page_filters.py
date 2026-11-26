"""HtmlPage: the filter rows its caller gives, shown in order, each only with two chips or more."""

import re

from hypothesis import given
from hypothesis import strategies as st
from red_thread_core.documents import Document, Paragraph, Section, parse_line
from red_thread_core.writers.page import Chip, HtmlPage

CHIP_ROW = re.compile(r'<div class="chips" role="group" aria-label="Filter by ([^"]*)">')
TWO_CHIPS = 2


def create_row(group: str, size: int) -> tuple[Chip, ...]:
    return tuple(
        Chip(group=group, value=f'v{index}', label=f'v{index}', count=1) for index in range(size)
    )


def create_rows(sizes: list[int]) -> tuple[tuple[Chip, ...], ...]:
    return tuple(create_row(f'g{index}', size) for index, size in enumerate(sizes))


def create_document(*, sections: bool) -> Document:
    section = Section(title='s', blocks=(Paragraph(line=parse_line('a')),))
    return Document(title='t', sections=(section,) if sections else ())


class TestPageFilters:
    sizes = st.lists(st.integers(min_value=0, max_value=4), max_size=4)

    @given(sizes=sizes)
    def test_a_row_shows_in_order_when_it_has_two_chips_or_more(self, sizes: list[int]) -> None:
        page = HtmlPage(document=create_document(sections=True), filters=create_rows(sizes))

        shown = CHIP_ROW.findall(page.render())
        assert shown == [f'g{index}' for index, size in enumerate(sizes) if size >= TWO_CHIPS]

    @given(sizes=sizes)
    def test_a_page_without_sections_shows_no_row(self, sizes: list[int]) -> None:
        page = HtmlPage(document=create_document(sections=False), filters=create_rows(sizes))

        assert CHIP_ROW.findall(page.render()) == []
