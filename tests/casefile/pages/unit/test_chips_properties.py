"""Filter chips: counts, order and the two-chip rule, from the page and from the rendered page."""

from collections import Counter
from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.charts import MAIN_LEDGER
from red_thread_casefile.documents import FindingNode, list_document_findings, list_findings_block
from red_thread_casefile.domain import FINDING_KINDS
from red_thread_casefile.packaged import load_wording
from red_thread_casefile.writers.page import (
    list_kind_chips,
    list_thread_chips,
    order_name,
    render_case_page,
)
from red_thread_core.documents import Document, PointList, Section, parse_line

from tests.casefile.findings.strategies import optional, thread_names
from tests.casefile.pages.html_reading import (
    ChipReading,
    find_buttons,
    find_tags,
    list_chip_groups,
)
from tests.core.timekeeping.clock import DAY

if TYPE_CHECKING:
    from collections.abc import Sequence

    from red_thread_core.documents import Block, Line
    from red_thread_core.writers.page import Chip

TWO_CHIPS = 2

type Member = FindingNode | Line


def name_group(group: list[ChipReading]) -> str:
    return group[0].group


def read_chip(chip: Chip) -> ChipReading:
    return ChipReading(group=chip.group, value=chip.value, label=chip.label, count=chip.count)


def list_points_block(points: tuple[Line, ...]) -> tuple[Block, ...]:
    if not points:
        return ()
    return (PointList(points=points),)


def create_section(number: int, group: Sequence[Member]) -> Section:
    findings = tuple(member for member in group if isinstance(member, FindingNode))
    points = tuple(member for member in group if not isinstance(member, FindingNode))
    blocks = (*list_points_block(points), *list_findings_block(findings))
    return Section(title=f'Section {number}', blocks=blocks)


def create_sectioned_document(groups: Sequence[Sequence[Member]]) -> Document:
    sections = tuple(create_section(number, group) for number, group in enumerate(groups, 1))
    return Document(title='t', sections=sections)


def expect_kind_chips(document: Document) -> list[ChipReading]:
    counted = Counter(finding.kind for finding in list_document_findings(document))
    return [
        ChipReading(
            group='kind',
            value=heading.kind,
            label=heading.title,
            count=counted[heading.kind],
        )
        for heading in load_wording().headings
        if counted[heading.kind]
    ]


def expect_thread_chips(document: Document) -> list[ChipReading]:
    counted = Counter(finding.thread or '' for finding in list_document_findings(document))
    main = [''] * ('' in counted)
    named = sorted((name for name in counted if name), key=order_name)
    return [
        ChipReading(group='thread', value=name, label=name or MAIN_LEDGER, count=counted[name])
        for name in (*main, *named)
    ]


class TestChipProperties:
    odd_threads = st.text(alphabet='abT019', min_size=1, max_size=3)
    findings = st.builds(
        FindingNode,
        finding_id=st.just('e1'),
        kind=st.sampled_from(FINDING_KINDS),
        claim=st.just(parse_line('a claim')),
        round=st.just(1),
        at=st.just(DAY),
        thread=optional(st.one_of(thread_names, odd_threads)),
    )
    points = st.just(parse_line('a pointer'))
    groups = st.lists(st.lists(st.one_of(findings, points), max_size=4), max_size=3)
    documents = groups.map(create_sectioned_document)

    @given(document=documents)
    def test_kind_chips_count_the_findings_of_each_kind_in_the_order_of_the_sections(
        self, document: Document
    ) -> None:
        chips = list_kind_chips(list_document_findings(document), load_wording().headings)

        assert list(map(read_chip, chips)) == expect_kind_chips(document)

    @given(document=documents)
    def test_thread_chips_put_the_main_ledger_first_then_names_by_length_and_text(
        self, document: Document
    ) -> None:
        chips = list_thread_chips(list_document_findings(document))

        assert list(map(read_chip, chips)) == expect_thread_chips(document)

    @given(document=documents)
    def test_a_point_is_counted_by_no_chip(self, document: Document) -> None:
        findings = list_document_findings(document)

        assert sum(
            chip.count for chip in list_kind_chips(findings, load_wording().headings)
        ) == len(findings)
        assert sum(chip.count for chip in list_thread_chips(findings)) == len(findings)

    @given(document=documents)
    def test_the_page_shows_a_chip_group_only_for_a_filter_with_two_or_more_chips(
        self, document: Document
    ) -> None:
        page = render_case_page(document, load_wording().headings)

        shown = list_chip_groups(page)
        offered = [expect_kind_chips(document), expect_thread_chips(document)]
        expected = [chips for chips in offered if len(chips) >= TWO_CHIPS and document.sections]
        assert sorted(shown, key=name_group) == expected

    @given(document=documents)
    def test_the_toolbar_exists_exactly_when_there_is_a_section_and_holds_one_fold_button(
        self, document: Document
    ) -> None:
        page = render_case_page(document, load_wording().headings)

        toolbars = [nav for nav in find_tags(page, 'nav') if nav['class'] == 'toolbar']
        folds = [tool for tool in find_buttons(page, 'tool') if 'data-fold' in tool]
        assert len(toolbars) == len(folds) == bool(document.sections)
