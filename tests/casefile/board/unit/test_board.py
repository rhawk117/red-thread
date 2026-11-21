"""The board: its sections, its cap, its lead marker and what it leaves out."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.domain import Ledger
from red_thread_casefile.views import Board, BoardOptions

from tests.casefile.board.cases import lead_marker_params, section_cap_params
from tests.casefile.ledger.builders import create_case, create_draft, create_entry
from tests.casefile.ledger.memory import HEAD, NEXT_HEAD

if TYPE_CHECKING:
    from red_thread_casefile.domain import Entry

    from tests.casefile.board.cases import CapCase, LeadCase
    from tests.casefile.ledger.builders import CaseHarness

SECTION_TITLES = ['Decided', 'Known', 'Hypotheses', 'Open', 'Ruled out', 'Next', 'Resources']


def create_board(
    entries: tuple[Entry, ...], head: str | None = HEAD, options: BoardOptions | None = None
) -> Board:
    return Board(
        case=create_case(),
        ledger=Ledger(entries=entries),
        head=head,
        options=options or BoardOptions(),
    )


def list_headings(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith('## ')]


def list_refs(text: str) -> list[str]:
    lines = (line for line in text.splitlines() if line.startswith('- ['))
    return [line.split(']')[0].removeprefix('- [') for line in lines]


def create_known_entries(count: int) -> tuple[Entry, ...]:
    return tuple(
        create_entry(seq=seq, kind='known', cite='https://example.invalid/a', text=f'finding {seq}')
        for seq in range(1, count + 1)
    )


def section_cap_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', section_cap_params())


def lead_marker_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', lead_marker_params())


class TestSections:
    def test_sections_come_in_the_documented_order(self) -> None:
        kinds = ('resource', 'next', 'ruled_out', 'open', 'hypothesis', 'known', 'decision')
        entries = tuple(create_entry(seq=seq, kind=kind) for seq, kind in enumerate(kinds, 1))

        text = create_board(entries).render()

        headings = [heading.removeprefix('## ').split(' (')[0] for heading in list_headings(text)]
        assert headings == SECTION_TITLES

    def test_a_section_with_no_live_entry_is_left_out(self) -> None:
        entries = (create_entry(seq=1, kind='open'), create_entry(seq=2, kind='next'))

        headings = list_headings(create_board(entries).render())

        assert headings == ['## Open (1)', '## Next (1)']

    def test_empty_ledger_has_a_header_and_no_section(self) -> None:
        text = create_board(()).render()

        assert list_headings(text) == []
        assert 'Entries: 0 live, 0 retired' in text

    def test_header_names_the_case_the_round_the_head_and_the_threads(self) -> None:
        entries = (
            create_entry(seq=1, round_number=2),
            create_entry(seq=1, thread='T1', round_number=3),
            create_entry(seq=2, thread='T1'),
        )

        text = create_board(entries).render()

        assert text.splitlines()[0] == '# 20261121-retry-queue-slowdown'
        assert 'Target: why the retry queue stalls' in text
        assert 'Kind: root-cause | Round: 3 | HEAD: 1111111' in text
        assert 'Threads: T1 (2)' in text

    def test_thread_entries_are_listed_under_their_thread_ref(self) -> None:
        entries = (create_entry(seq=1), create_entry(seq=1, thread='T1'))

        refs = list_refs(create_board(entries).render())

        assert sorted(refs) == ['T1.e1', 'e1']

    def test_verdict_and_caveat_of_an_open_entry_are_shown(self) -> None:
        entry = create_entry(seq=1, verdict='INFERRED', rests_on='a 4.x docs page')

        text = create_board((entry,)).render()

        assert '- [e1] INFERRED: the retry queue stalls' in text
        assert 'rests on: a 4.x docs page' in text


class TestSectionCap:
    @section_cap_cases()
    def test_section_shows_its_latest_entries_and_counts_the_hidden_ones(
        self, case: CapCase
    ) -> None:
        text = create_board(create_known_entries(case.total)).render()

        assert list_refs(text) == [f'e{seq}' for seq in case.shown_seqs]
        assert f'## Known ({case.total})' in text
        hidden_line = f'(+{case.hidden} earlier, shown by render --full)'
        assert (hidden_line in text) is (case.hidden > 0)

    def test_each_section_is_capped_on_its_own(self) -> None:
        known = create_known_entries(7)
        opened = tuple(create_entry(seq=seq + 7, kind='open') for seq in range(1, 9))

        text = create_board((*known, *opened)).render()

        assert '(+1 earlier, shown by render --full)' in text
        assert '(+2 earlier, shown by render --full)' in text
        assert len(list_refs(text)) == 12

    def test_full_preset_shows_every_live_entry(self) -> None:
        board = create_board(create_known_entries(40), options=BoardOptions.full())

        text = board.render()

        assert len(list_refs(text)) == 40
        assert 'earlier' not in text

    def test_default_options_cap_each_section_at_six(self) -> None:
        assert BoardOptions().per_section == 6


class TestRetiredEntries:
    def test_retired_entry_leaves_its_section_and_is_counted_as_retired(self) -> None:
        entries = (
            create_entry(seq=1, kind='known', cite='https://example.invalid/a'),
            create_entry(seq=2, kind='open', supersedes=('e1',)),
        )

        text = create_board(entries).render()

        assert list_refs(text) == ['e2']
        assert 'Entries: 1 live, 1 retired' in text
        assert 'Known' not in text

    def test_retiring_the_only_entry_of_a_section_removes_the_section(self) -> None:
        entries = (create_entry(seq=1, kind='hypothesis'), create_entry(seq=2, supersedes=('e1',)))

        assert 'Hypotheses' not in create_board(entries).render()

    def test_thread_entry_retired_by_its_thread_leaves_the_board(self) -> None:
        entries = (
            create_entry(seq=1, thread='T1', text='first guess'),
            create_entry(seq=2, thread='T1', text='better guess', supersedes=('T1.e1',)),
        )

        text = create_board(entries).render()

        assert list_refs(text) == ['T1.e2']
        assert 'first guess' not in text

    def test_retired_entry_is_not_counted_in_its_section(self) -> None:
        known = create_known_entries(7)
        retiring = create_entry(seq=8, kind='open', supersedes=('e1',))

        text = create_board((*known, retiring)).render()

        assert '## Known (6)' in text
        assert 'earlier' not in text


class TestLeadMarker:
    @lead_marker_cases()
    def test_entry_recorded_at_another_head_is_a_lead(self, case: LeadCase) -> None:
        entry = create_entry(seq=1, head=case.entry_head)

        text = create_board((entry,), head=case.board_head).render()

        assert ('lead, recorded at' in text) is case.is_lead
        if case.recorded is not None:
            assert f'lead, recorded at {case.recorded}' in text

    def test_only_the_entries_recorded_at_another_head_are_leads(self) -> None:
        stale = create_entry(seq=1, head=NEXT_HEAD, text='stale claim')
        current = create_entry(seq=2, head=HEAD, text='current claim')

        text = create_board((stale, current)).render()

        lines = {line.split(']')[0]: line for line in text.splitlines() if line.startswith('- [')}
        assert 'lead' in lines['- [e1']
        assert 'lead' not in lines['- [e2']


class TestShow:
    @pytest.fixture
    def harness(self, framed_harness: CaseHarness) -> CaseHarness:
        framed_harness.add(create_draft())
        return framed_harness

    def test_shown_board_lists_what_was_added(self, harness: CaseHarness) -> None:
        text = harness.casefile.show()

        assert '[e1]' in text
        assert 'lead' not in text

    def test_entries_become_leads_when_the_tree_moves_on(self, harness: CaseHarness) -> None:
        harness.tree.advance(NEXT_HEAD)

        text = harness.casefile.show()

        assert 'lead, recorded at 1111111' in text

    def test_show_applies_the_options_it_is_given(self, framed_harness: CaseHarness) -> None:
        framed_harness.seed(None, *create_known_entries(8))

        capped = framed_harness.casefile.show()
        full = framed_harness.casefile.show(BoardOptions.full())

        assert len(list_refs(capped)) == 6
        assert len(list_refs(full)) == 8
