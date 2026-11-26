"""Filter chips: counts, order and the two-chip rule, from the page and from the rendered page."""

from collections import Counter
from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.charts import MAIN_LEDGER
from red_thread_casefile.documents import (
    Document,
    EntryNode,
    PointList,
    Section,
    list_entries_block,
    parse_line,
)
from red_thread_casefile.domain import ENTRY_KINDS
from red_thread_casefile.views import HEADINGS
from red_thread_casefile.writers.page import HtmlPage, order_name

from tests.casefile.documents.builders import MOMENT
from tests.casefile.entries.strategies import optional, thread_names
from tests.casefile.pages.html_reading import (
    ChipReading,
    find_buttons,
    find_tags,
    list_chip_groups,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from red_thread_casefile.documents import Block, Line
    from red_thread_casefile.writers.page import Chip

TWO_CHIPS = 2

type Member = EntryNode | Line


def name_group(group: list[ChipReading]) -> str:
    return group[0].group


def read_chip(chip: Chip) -> ChipReading:
    return ChipReading(group=chip.group, value=chip.value, label=chip.label, count=chip.count)


def list_points_block(points: tuple[Line, ...]) -> tuple[Block, ...]:
    if not points:
        return ()
    return (PointList(points=points),)


def create_section(number: int, group: Sequence[Member]) -> Section:
    entries = tuple(member for member in group if isinstance(member, EntryNode))
    points = tuple(member for member in group if not isinstance(member, EntryNode))
    blocks = (*list_points_block(points), *list_entries_block(entries))
    return Section(title=f'Section {number}', blocks=blocks)


def create_sectioned_document(groups: Sequence[Sequence[Member]]) -> Document:
    sections = tuple(create_section(number, group) for number, group in enumerate(groups, 1))
    return Document(title='t', sections=sections)


def expect_kind_chips(document: Document) -> list[ChipReading]:
    counted = Counter(entry.kind for entry in document.entries)
    return [
        ChipReading(
            group='kind',
            value=heading.kind,
            label=heading.title,
            count=counted[heading.kind],
        )
        for heading in HEADINGS
        if counted[heading.kind]
    ]


def expect_thread_chips(document: Document) -> list[ChipReading]:
    counted = Counter(entry.thread or '' for entry in document.entries)
    main = [''] * ('' in counted)
    named = sorted((name for name in counted if name), key=order_name)
    return [
        ChipReading(group='thread', value=name, label=name or MAIN_LEDGER, count=counted[name])
        for name in (*main, *named)
    ]


class TestChipProperties:
    odd_threads = st.text(alphabet='abT019', min_size=1, max_size=3)
    entries = st.builds(
        EntryNode,
        ref=st.just('e1'),
        kind=st.sampled_from(ENTRY_KINDS),
        claim=st.just(parse_line('a claim')),
        round=st.just(1),
        at=st.just(MOMENT),
        thread=optional(st.one_of(thread_names, odd_threads)),
    )
    points = st.just(parse_line('a pointer'))
    groups = st.lists(st.lists(st.one_of(entries, points), max_size=4), max_size=3)
    documents = groups.map(create_sectioned_document)

    @given(document=documents)
    def test_kind_chips_count_the_entries_of_each_kind_in_the_order_of_the_sections(
        self, document: Document
    ) -> None:
        chips = HtmlPage(document=document).list_kind_chips()

        assert list(map(read_chip, chips)) == expect_kind_chips(document)

    @given(document=documents)
    def test_thread_chips_put_the_main_ledger_first_then_names_by_length_and_text(
        self, document: Document
    ) -> None:
        chips = HtmlPage(document=document).list_thread_chips()

        assert list(map(read_chip, chips)) == expect_thread_chips(document)

    @given(document=documents)
    def test_a_point_is_counted_by_no_chip(self, document: Document) -> None:
        page = HtmlPage(document=document)
        entries = document.entries

        assert sum(chip.count for chip in page.list_kind_chips()) == len(entries)
        assert sum(chip.count for chip in page.list_thread_chips()) == len(entries)

    @given(document=documents)
    def test_the_page_shows_a_chip_group_only_for_a_filter_with_two_or_more_chips(
        self, document: Document
    ) -> None:
        page = HtmlPage(document=document).render()

        shown = list_chip_groups(page)
        offered = [expect_kind_chips(document), expect_thread_chips(document)]
        expected = [chips for chips in offered if len(chips) >= TWO_CHIPS and document.sections]
        assert sorted(shown, key=name_group) == expected

    @given(document=documents)
    def test_the_toolbar_exists_exactly_when_there_is_a_section_and_holds_one_fold_button(
        self, document: Document
    ) -> None:
        page = HtmlPage(document=document).render()

        navs = find_tags(page, 'nav')
        folds = [tool for tool in find_buttons(page, 'tool') if 'data-fold' in tool]
        assert len(navs) == len(folds) == bool(document.sections)
        assert all(nav['class'] == 'toolbar' for nav in navs)
