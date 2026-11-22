"""Filter chips: counts, order and the two-chip rule, from the writer and from the rendered page."""

from collections import Counter
from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.domain import ENTRY_KINDS
from red_thread_casefile.pages import HtmlWriter
from red_thread_casefile.views import SECTIONS, Document, Item, Section

from tests.casefile.entries.strategies import optional, thread_names
from tests.casefile.pages.html_reading import (
    ChipReading,
    find_buttons,
    find_tags,
    list_chip_groups,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from red_thread_casefile.pages import Chip

MAIN_LEDGER_LABEL = 'main ledger'
TWO_CHIPS = 2


def order_name(name: str) -> tuple[int, str]:
    return (len(name), name)


def name_group(group: list[ChipReading]) -> str:
    return group[0].group


def read_chip(chip: Chip) -> ChipReading:
    return ChipReading(group=chip.group, value=chip.value, label=chip.label, count=chip.count)


def create_sectioned_document(groups: Sequence[Sequence[Item]]) -> Document:
    sections = tuple(
        Section(title=f'Section {number}', items=tuple(group))
        for number, group in enumerate(groups, 1)
    )
    return Document(title='t', sections=sections)


def list_entries(document: Document) -> list[Item]:
    items = (item for section in document.sections for item in section.items)
    return [item for item in items if item.ref is not None]


def expect_kind_chips(document: Document) -> list[ChipReading]:
    counted = Counter(item.kind for item in list_entries(document))
    return [
        ChipReading(group='kind', value=kind, label=title, count=counted[kind])
        for kind, title in SECTIONS
        if counted[kind]
    ]


def expect_thread_chips(document: Document) -> list[ChipReading]:
    counted = Counter(item.thread or '' for item in list_entries(document))
    main = [''] * ('' in counted)
    named = sorted((name for name in counted if name), key=order_name)
    return [
        ChipReading(
            group='thread', value=name, label=name or MAIN_LEDGER_LABEL, count=counted[name]
        )
        for name in (*main, *named)
    ]


class TestChipProperties:
    odd_threads = st.text(alphabet='abT019', min_size=1, max_size=3)
    items = st.builds(
        Item,
        text=st.just('a claim'),
        ref=optional(st.just('e1')),
        kind=st.sampled_from(ENTRY_KINDS),
        thread=optional(st.one_of(thread_names, odd_threads)),
    )
    groups = st.lists(st.lists(items, max_size=4), max_size=3)
    documents = groups.map(create_sectioned_document)

    @given(document=documents)
    def test_kind_chips_count_the_entries_of_each_kind_in_the_order_of_the_sections(
        self, document: Document
    ) -> None:
        chips = HtmlWriter(document=document).list_kind_chips()

        assert list(map(read_chip, chips)) == expect_kind_chips(document)

    @given(document=documents)
    def test_thread_chips_put_the_main_ledger_first_then_names_by_length_and_text(
        self, document: Document
    ) -> None:
        chips = HtmlWriter(document=document).list_thread_chips()

        assert list(map(read_chip, chips)) == expect_thread_chips(document)

    @given(document=documents)
    def test_an_item_with_no_ref_is_counted_by_no_chip(self, document: Document) -> None:
        writer = HtmlWriter(document=document)
        entries = list_entries(document)

        assert sum(chip.count for chip in writer.list_kind_chips()) == len(entries)
        assert sum(chip.count for chip in writer.list_thread_chips()) == len(entries)

    @given(document=documents)
    def test_the_page_shows_a_chip_group_only_for_a_filter_with_two_or_more_chips(
        self, document: Document
    ) -> None:
        page = HtmlWriter(document=document).render()

        shown = list_chip_groups(page)
        offered = [expect_kind_chips(document), expect_thread_chips(document)]
        expected = [chips for chips in offered if len(chips) >= TWO_CHIPS and document.sections]
        assert sorted(shown, key=name_group) == expected

    @given(document=documents)
    def test_the_toolbar_exists_exactly_when_there_is_a_section_and_holds_one_fold_button(
        self, document: Document
    ) -> None:
        page = HtmlWriter(document=document).render()

        navs = find_tags(page, 'nav')
        folds = [tool for tool in find_buttons(page, 'tool') if 'data-fold' in tool]
        assert len(navs) == len(folds) == bool(document.sections)
        assert all(nav['class'] == 'toolbar' for nav in navs)
