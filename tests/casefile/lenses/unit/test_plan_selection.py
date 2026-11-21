"""export: how a plan selects, orders and labels entries."""

from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.lenses import Plan

from tests.casefile.ledger.builders import create_entry
from tests.casefile.lenses.builders import create_numbered_entries, create_press_harness
from tests.casefile.lenses.cases import QUEUE_CITE, QUEUE_QUOTE, lens_with_decisions_params
from tests.casefile.lenses.reading import (
    find_item,
    list_headings,
    list_refs,
    list_remarks,
    list_section_lines,
)

if TYPE_CHECKING:
    from red_thread_casefile.lenses import LensName

    from tests.casefile.lenses.builders import PressHarness

URGENCY_LABELS = ('blocking', 'not blocking')


def read_urgency(text: str, ref: str) -> str | None:
    labels = [remark for remark in list_remarks(find_item(text, ref)) if remark in URGENCY_LABELS]
    return next(iter(labels), None)


def lens_with_decisions_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('lens', lens_with_decisions_params())


class TestWithoutAPlan:
    @pytest.fixture
    def stocked(self, press_harness: PressHarness) -> PressHarness:
        press_harness.seed(
            create_entry(seq=1, kind='open', text='zulu question'),
            create_entry(
                seq=2, kind='known', text='yankee finding', cite=QUEUE_CITE, quote=QUEUE_QUOTE
            ),
            create_entry(
                seq=3, kind='known', text='alpha finding', cite=QUEUE_CITE, quote=QUEUE_QUOTE
            ),
            create_entry(seq=4, kind='open', text='alpha question'),
            create_entry(seq=5, kind='hypothesis', text='a guess', refute='the stall ends'),
            create_entry(seq=6, kind='decision', text='keep retries', source='user'),
            create_entry(seq=7, kind='open', text='middle question'),
            create_entry(seq=8, kind='next', text='read the scheduler'),
            create_entry(seq=9, kind='resource', text='the scheduler docs'),
            create_entry(
                seq=10, kind='ruled_out', text='not the network', cite=QUEUE_CITE, quote=QUEUE_QUOTE
            ),
        )
        press_harness.seed_thread(
            'T1', create_entry(seq=1, thread='T1', kind='open', text='lead question')
        )
        return press_harness

    def test_every_live_entry_appears_in_ledger_order(self, stocked: PressHarness) -> None:
        text = stocked.export_markdown('report')

        assert list_refs(text, 'Open') == ['e1', 'e4', 'e7', 'T1.e1']
        assert list_refs(text, 'Findings') == ['e2', 'e3']
        assert list_refs(text, 'Decided') == ['e6']
        assert list_refs(text, 'Hypotheses') == ['e5']
        assert list_refs(text, 'Next steps') == ['e8']
        assert list_refs(text, 'Resources') == ['e9']
        assert list_refs(text, 'Ruled out') == ['e10']

    def test_open_entries_carry_no_urgency_label_without_the_blocking_key(
        self, stocked: PressHarness
    ) -> None:
        text = stocked.export_markdown('report')

        assert read_urgency(text, 'e1') is None
        assert read_urgency(text, 'T1.e1') is None

    def test_a_plan_with_only_a_title_still_lists_every_live_entry(
        self, stocked: PressHarness
    ) -> None:
        text = stocked.export_markdown('report', Plan(title='A title'))

        assert list_refs(text, 'Open') == ['e1', 'e4', 'e7', 'T1.e1']


class TestInclude:
    @pytest.fixture
    def stocked(self, press_harness: PressHarness) -> PressHarness:
        press_harness.seed(*create_numbered_entries('known', 4))
        return press_harness

    def test_include_selects_and_orders_entries(self, stocked: PressHarness) -> None:
        text = stocked.export_markdown('brief', Plan(include=('e3', 'e1')))

        assert list_refs(text, 'Constraints') == ['e3', 'e1']

    def test_include_order_beats_ledger_order(self, stocked: PressHarness) -> None:
        text = stocked.export_markdown('brief', Plan(include=('e4', 'e3', 'e2', 'e1')))

        assert list_refs(text, 'Constraints') == ['e4', 'e3', 'e2', 'e1']

    def test_an_empty_include_keeps_no_entry_but_the_decisions(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(
            create_entry(seq=1, kind='known', text='a finding'),
            create_entry(seq=2, kind='open', text='a question'),
            create_entry(seq=3, kind='decision', text='a decision', source='user'),
        )

        text = press_harness.export_markdown('brief', Plan(include=()))

        assert list_headings(text) == ['Goal', 'Decided', 'Pointers', 'How to read']
        assert list_refs(text, 'Decided') == ['e3']

    def test_entries_the_include_names_across_kinds_each_keep_their_section(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(
            create_entry(seq=1, kind='known', text='a finding'),
            create_entry(seq=2, kind='open', text='a question'),
            create_entry(seq=3, kind='open', text='another question'),
        )

        text = press_harness.export_markdown('brief', Plan(include=('e3', 'e1')))

        assert list_refs(text, 'Constraints') == ['e1']
        assert list_refs(text, 'Open') == ['e3']


class TestIncludeProperty:
    ref_picks = st.lists(st.integers(min_value=1, max_value=8), unique=True)

    def export_with_include(self, picks: list[int]) -> str:
        harness = create_press_harness()
        harness.seed(*create_numbered_entries('known', 8))
        include = tuple(f'e{pick}' for pick in picks)
        return harness.export_markdown('brief', Plan(include=include))

    @given(picks=ref_picks)
    def test_the_section_lists_exactly_the_included_refs_in_include_order(
        self, picks: list[int]
    ) -> None:
        text = self.export_with_include(picks)

        assert list_refs(text, 'Constraints') == [f'e{pick}' for pick in picks]


class TestDecisions:
    @pytest.fixture
    def stocked(self, press_harness: PressHarness) -> PressHarness:
        press_harness.seed(
            create_entry(seq=1, kind='decision', text='keep retries', source='user'),
            create_entry(seq=2, kind='decision', text='ship on friday', source='user'),
            create_entry(seq=3, kind='known', text='a finding', cite=QUEUE_CITE, quote=QUEUE_QUOTE),
        )
        return press_harness

    @lens_with_decisions_cases()
    def test_decisions_appear_even_when_include_names_none_of_them(
        self, stocked: PressHarness, lens: LensName
    ) -> None:
        text = stocked.export_markdown(lens, Plan(include=('e3',)))

        assert sorted(list_refs(text, 'Decided')) == ['e1', 'e2']

    def test_a_decision_the_include_names_is_ordered_by_it(self, stocked: PressHarness) -> None:
        text = stocked.export_markdown('brief', Plan(include=('e2', 'e1')))

        assert list_refs(text, 'Decided') == ['e2', 'e1']

    def test_a_decision_stays_when_the_plan_blocks_other_entries(
        self, stocked: PressHarness
    ) -> None:
        stocked.seed(create_entry(seq=4, kind='open', text='a question'))

        text = stocked.export_markdown('brief', Plan(include=(), blocking=('e4',)))

        assert sorted(list_refs(text, 'Decided')) == ['e1', 'e2']


class TestBlocking:
    @pytest.fixture
    def stocked(self, press_harness: PressHarness) -> PressHarness:
        press_harness.seed(*create_numbered_entries('open', 5))
        return press_harness

    def test_blocking_entries_sort_first_and_the_rest_keep_ledger_order(
        self, stocked: PressHarness
    ) -> None:
        text = stocked.export_markdown('brief', Plan(blocking=('e4',)))

        assert list_refs(text, 'Open') == ['e4', 'e1', 'e2', 'e3', 'e5']

    def test_blocking_entry_the_include_leaves_out_still_appears_first(
        self, stocked: PressHarness
    ) -> None:
        text = stocked.export_markdown('brief', Plan(include=('e1',), blocking=('e3',)))

        assert list_refs(text, 'Open') == ['e3', 'e1']

    def test_blocking_sorts_ahead_of_the_include_order(self, stocked: PressHarness) -> None:
        plan = Plan(include=('e4', 'e2'), blocking=('e3',))

        text = stocked.export_markdown('brief', plan)

        assert list_refs(text, 'Open') == ['e3', 'e4', 'e2']

    def test_blocking_entry_the_include_also_names_still_sorts_first(
        self, stocked: PressHarness
    ) -> None:
        text = stocked.export_markdown('brief', Plan(include=('e2', 'e5'), blocking=('e5',)))

        assert list_refs(text, 'Open') == ['e5', 'e2']

    def test_open_entries_are_labelled_blocking_or_not_blocking(
        self, stocked: PressHarness
    ) -> None:
        text = stocked.export_markdown('brief', Plan(blocking=('e4',)))

        assert read_urgency(text, 'e4') == 'blocking'
        assert [read_urgency(text, ref) for ref in ('e1', 'e2', 'e3', 'e5')] == ['not blocking'] * 4

    def test_an_empty_blocking_list_still_labels_every_open_entry_not_blocking(
        self, stocked: PressHarness
    ) -> None:
        text = stocked.export_markdown('brief', Plan(blocking=()))

        labels = {read_urgency(text, ref) for ref in list_refs(text, 'Open')}
        assert labels == {'not blocking'}

    def test_a_plan_without_the_blocking_key_labels_nothing(self, stocked: PressHarness) -> None:
        text = stocked.export_markdown('brief', Plan(include=('e2', 'e1')))

        assert list_refs(text, 'Open') == ['e2', 'e1']
        assert {read_urgency(text, ref) for ref in ('e1', 'e2')} == {None}

    def test_an_urgency_label_shares_the_parentheses_with_the_caveat(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(create_entry(seq=1, kind='open', rests_on='a docs page'))

        text = press_harness.export_markdown('brief', Plan(blocking=('e1',)))

        remarks = list_remarks(find_item(text, 'e1'))
        assert remarks == ['blocking', 'rests on: a docs page']

    def test_only_open_entries_are_labelled(self, press_harness: PressHarness) -> None:
        press_harness.seed(
            create_entry(seq=1, kind='known', text='a finding', cite=QUEUE_CITE, quote=QUEUE_QUOTE),
            create_entry(seq=2, kind='open', text='a question'),
        )

        text = press_harness.export_markdown('brief', Plan(blocking=('e2',)))

        assert list_section_lines(text, 'Constraints') == ['- a finding `src/queue.py:3` [e1]']
        assert read_urgency(text, 'e2') == 'blocking'


class TestBlockingProperty:
    blocked_picks = st.lists(st.integers(min_value=1, max_value=6), unique=True)

    def export_with_blocking(self, picks: list[int]) -> str:
        harness = create_press_harness()
        harness.seed(*create_numbered_entries('open', 6))
        blocking = tuple(f'e{pick}' for pick in picks)
        return harness.export_markdown('brief', Plan(blocking=blocking))

    @given(picks=blocked_picks)
    def test_blocking_entries_come_first_and_every_entry_is_labelled_by_membership(
        self, picks: list[int]
    ) -> None:
        text = self.export_with_blocking(picks)

        refs = list_refs(text, 'Open')
        labels = [read_urgency(text, ref) for ref in refs]
        blocked = {f'e{pick}' for pick in picks}
        assert sorted(refs) == sorted(f'e{number}' for number in range(1, 7))
        assert labels == ['blocking' if ref in blocked else 'not blocking' for ref in refs]
        assert labels == ['blocking'] * len(picks) + ['not blocking'] * (6 - len(picks))
