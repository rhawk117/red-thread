"""export: the sections a lens writes, their order and the words each finding carries."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.domain import FINDING_KINDS
from red_thread_casefile.lenses import Selection

from tests.casefile.ledger.builders import CASE_ID, URL_CITE, create_finding
from tests.casefile.lenses.builders import create_numbered_findings
from tests.casefile.lenses.cases import (
    QUEUE_CITE,
    QUEUE_QUOTE,
    citation_shape_params,
    lens_shape_params,
)
from tests.casefile.lenses.reading import (
    find_item,
    list_all_finding_ids,
    list_finding_ids,
    list_headings,
    list_remarks,
    list_section_lines,
)

if TYPE_CHECKING:
    from tests.casefile.lenses.builders import PressHarness
    from tests.casefile.lenses.cases import CitationShape, LensShape


def lens_shape_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('shape', lens_shape_params())


def citation_shape_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('shape', citation_shape_params())


class TestPartOrder:
    @pytest.fixture
    def stocked(self, press_harness: PressHarness) -> PressHarness:
        findings = (
            create_finding(
                finding_number=finding_number,
                kind=kind,
                text=f'a {kind} finding',
                citation=URL_CITE,
                source='user',
            )
            for finding_number, kind in enumerate(FINDING_KINDS, 1)
        )
        press_harness.seed(*findings)
        return press_harness

    @lens_shape_cases()
    def test_sections_follow_the_lens_part_order(
        self, stocked: PressHarness, shape: LensShape
    ) -> None:
        text = stocked.export_markdown(shape.name)

        assert list_headings(text) == list(shape.headings)

    def test_brief_leaves_out_the_kinds_it_has_no_part_for(self, stocked: PressHarness) -> None:
        text = stocked.export_markdown('brief')

        assert 'a hypothesis finding' not in text
        assert 'a next finding' not in text
        assert 'a resource finding' not in text
        assert 'a decision finding' in text
        assert 'a known finding' in text

    def test_brief_puts_each_kind_under_its_own_heading(self, stocked: PressHarness) -> None:
        text = stocked.export_markdown('brief')

        assert list_finding_ids(text, 'Decided') == ['e3']
        assert list_finding_ids(text, 'Constraints') == ['e1']
        assert list_finding_ids(text, 'Ruled out') == ['e5']
        assert list_finding_ids(text, 'Open') == ['e2']


class TestEmptySections:
    def test_a_section_with_no_live_finding_is_left_out(self, press_harness: PressHarness) -> None:
        press_harness.seed(
            *create_numbered_findings('known', 1), create_finding(finding_number=2, kind='open')
        )

        text = press_harness.export_markdown('brief')

        assert list_headings(text) == ['Goal', 'Constraints', 'Open', 'Pointers', 'How to read']

    def test_an_empty_ledger_keeps_only_the_fixed_parts(self, press_harness: PressHarness) -> None:
        text = press_harness.export_markdown('brief')

        assert list_headings(text) == ['Goal', 'Pointers', 'How to read']

    def test_retiring_the_only_finding_of_a_kind_removes_its_section(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(
            create_finding(finding_number=1, kind='known', citation=URL_CITE),
            create_finding(finding_number=2, kind='open', supersedes=('e1',)),
        )

        text = press_harness.export_markdown('brief')

        assert 'Constraints' not in list_headings(text)


class TestFindingWording:
    @citation_shape_cases()
    def test_item_is_text_then_citation_then_finding_id_exactly(
        self, press_harness: PressHarness, shape: CitationShape
    ) -> None:
        press_harness.seed(
            create_finding(
                finding_number=1,
                kind='known',
                text='the sleep blocks the queue',
                citation=shape.citation,
                quote=QUEUE_QUOTE,
            )
        )

        text = press_harness.export_markdown('brief')

        expected = f'- the sleep blocks the queue {shape.written} [e1]'
        assert list_section_lines(text, 'Constraints') == [expected]

    def test_finding_without_a_citation_has_only_text_and_finding_id(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(
            create_finding(finding_number=1, kind='open', text='who owns the retry queue')
        )

        text = press_harness.export_markdown('brief')

        assert list_section_lines(text, 'Open') == ['- who owns the retry queue [e1]']

    def test_whitespace_runs_in_the_text_collapse_so_the_finding_stays_one_line(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(
            create_finding(finding_number=1, kind='open', text='the queue\n   stalls\tafter  retry')
        )

        text = press_harness.export_markdown('brief')

        assert list_section_lines(text, 'Open') == ['- the queue stalls after retry [e1]']

    def test_thread_findings_carry_their_thread_finding_id(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(
            create_finding(finding_number=1, kind='open', text='from the main ledger')
        )
        press_harness.seed_thread(
            'T1', create_finding(finding_number=1, thread='T1', kind='open', text='from a lead')
        )

        text = press_harness.export_markdown('brief')

        assert list_finding_ids(text, 'Open') == ['e1', 'T1.e1']
        assert find_item(text, 'T1.e1') == '- from a lead [T1.e1]'

    def test_caveats_of_an_finding_are_written_beside_its_text(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(
            create_finding(
                finding_number=1, kind='open', rests_on='a docs page for another version'
            )
        )

        text = press_harness.export_markdown('brief')

        remarks = list_remarks(find_item(text, 'e1'))
        assert remarks == ['rests on: a docs page for another version']

    def test_retired_finding_never_appears(self, press_harness: PressHarness) -> None:
        press_harness.seed(
            create_finding(
                finding_number=1,
                kind='known',
                text='the old claim',
                citation=QUEUE_CITE,
                quote=QUEUE_QUOTE,
            ),
            create_finding(
                finding_number=2,
                kind='known',
                text='the new claim',
                citation=QUEUE_CITE,
                quote=QUEUE_QUOTE,
                supersedes=('e1',),
            ),
        )

        text = press_harness.export_markdown('report')

        assert 'the old claim' not in text
        assert list_all_finding_ids(text) == ['e2']


class TestTitleAndGoal:
    def test_without_a_selection_the_title_is_the_target_and_the_goal_is_target_and_bar(
        self, press_harness: PressHarness
    ) -> None:
        text = press_harness.export_markdown('brief')

        assert text.splitlines()[0] == '# why the retry queue stalls'
        goal = ' '.join(list_section_lines(text, 'Goal'))
        assert 'why the retry queue stalls' in goal
        assert 'name the line that stalls it' in goal

    def test_selection_title_replaces_the_target_as_title(
        self, press_harness: PressHarness
    ) -> None:
        text = press_harness.export_markdown('brief', Selection(title='Why jobs wait'))

        assert text.splitlines()[0] == '# Why jobs wait'

    def test_selection_goal_replaces_the_target_and_bar_in_the_goal(
        self, press_harness: PressHarness
    ) -> None:
        text = press_harness.export_markdown(
            'brief', Selection(goal='Decide whether to drop retries')
        )

        assert list_section_lines(text, 'Goal') == ['Decide whether to drop retries']

    def test_output_names_the_case(self, press_harness: PressHarness) -> None:
        text = press_harness.export_markdown('brief')

        assert CASE_ID in text
