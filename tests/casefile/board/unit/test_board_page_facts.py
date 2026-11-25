"""BoardPage: the header facts, their order, the page fact and the citation state count."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.boards import BoardPage

from tests.casefile.board.builders import create_case_with, create_finding, create_page_board
from tests.casefile.board.cases import state_count_params
from tests.casefile.documents.reading import join_line
from tests.casefile.ledger.builders import MOMENT, create_case, create_entry
from tests.casefile.ledger.memory import HEAD

if TYPE_CHECKING:
    from red_thread_casefile.documents import Fact
    from red_thread_casefile.views import Board

    from tests.casefile.board.cases import StateCount

LABELS = [
    'Bar',
    'Kind',
    'Round',
    'Commit',
    'Created',
    'Languages',
    'Entries',
    'Threads',
    'Citations',
]
PAGE_URL = 'https://claude.ai/artifact/retry-queue'


def state_count_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('scenario', state_count_params())


def read_facts(board: Board) -> dict[str, str]:
    return {fact.label: join_line(fact.value) for fact in BoardPage(board=board).list_facts()}


def find_fact(board: Board, label: str) -> Fact:
    return next(fact for fact in BoardPage(board=board).list_facts() if fact.label == label)


class TestBoardPageFacts:
    def test_the_facts_come_in_a_fixed_order_with_no_page_fact_before_a_link_is_recorded(
        self,
    ) -> None:
        facts = BoardPage(board=create_page_board(create_entry())).compose().facts

        assert [fact.label for fact in facts] == LABELS

    def test_the_bar_and_the_citation_count_are_wide_and_no_other_fact_is(self) -> None:
        facts = BoardPage(board=create_page_board(create_entry())).list_facts()

        assert {fact.label for fact in facts if fact.wide} == {'Bar', 'Citations'}

    def test_a_recorded_page_link_is_a_wide_fact_after_the_others(self) -> None:
        board = create_page_board(create_entry(), case=create_case_with(page_url=PAGE_URL))

        *others, page = BoardPage(board=board).list_facts()

        assert [fact.label for fact in others] == LABELS
        assert (page.label, join_line(page.value), page.wide) == ('Page', PAGE_URL, True)

    def test_the_case_fields_are_shown_as_they_are_written(self) -> None:
        facts = read_facts(create_page_board(create_entry(round_number=3)))

        assert facts['Bar'] == create_case().bar
        assert facts['Kind'] == create_case().kind
        assert facts['Created'] == MOMENT[:10]
        assert facts['Round'] == '3'

    def test_the_round_is_zero_for_an_empty_ledger(self) -> None:
        assert read_facts(create_page_board())['Round'] == '0'

    def test_the_commit_is_the_short_head_or_none(self) -> None:
        assert read_facts(create_page_board(head=HEAD))['Commit'] == HEAD[:7]
        assert read_facts(create_page_board(head=None))['Commit'] == 'none'

    def test_the_languages_are_listed_or_none(self) -> None:
        listed = create_page_board(case=create_case_with(languages=('python', 'go')))

        assert read_facts(listed)['Languages'] == 'python, go'
        assert read_facts(create_page_board())['Languages'] == 'none'

    def test_the_entry_count_splits_live_from_retired(self) -> None:
        board = create_page_board(
            create_entry(seq=1),
            create_entry(seq=2),
            create_entry(seq=3, supersedes=('e1',)),
        )

        assert read_facts(board)['Entries'] == '2 live, 1 retired'

    def test_the_threads_are_listed_in_thread_order_with_every_entry_each_holds(self) -> None:
        board = create_page_board(
            create_entry(seq=1, thread='T10'),
            create_entry(seq=1, thread='T2'),
            create_entry(seq=2, thread='T2'),
            create_entry(seq=3, thread='T2', supersedes=('T2.e1',)),
            create_entry(seq=1),
        )

        assert read_facts(board)['Threads'] == 'T2 (3), T10 (1)'

    def test_no_thread_is_none(self) -> None:
        assert read_facts(create_page_board(create_entry()))['Threads'] == 'none'


class TestBoardPageCitationCount:
    @state_count_cases()
    def test_the_citation_fact_counts_the_findings_by_state(self, scenario: StateCount) -> None:
        findings = tuple(
            create_finding(f'e{number}', state) for number, state in enumerate(scenario.states, 1)
        )

        board = create_page_board(create_entry(), findings=findings)

        assert join_line(find_fact(board, 'Citations').value) == scenario.written
        assert BoardPage(board=board).count_states() == scenario.written
