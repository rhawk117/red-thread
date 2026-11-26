"""The page script, run under Node against a fake DOM built from a rendered board."""

from typing import TYPE_CHECKING

import pytest

from tests.casefile.ledger.builders import create_entry
from tests.casefile.lenses.cases import QUEUE_CITE, QUEUE_QUOTE
from tests.casefile.pages.script import (
    ScriptHarness,
    choose_theme,
    click,
    click_chip,
    deny_clipboard,
    load,
    navigate,
    run_timers,
    switch_scheme,
    toggle,
)

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.lenses.builders import PressHarness
    from tests.casefile.pages.script import PageState

FLOW = 'flowchart LR\n  retry --> pool'
OLD_FLOW = 'flowchart LR\n  guess --> pool'
RETIRED = 'Retired'
RETIRED_INDEX = 3


@pytest.fixture
def script(node: str, tmp_path: Path, press_harness: PressHarness) -> ScriptHarness:
    press_harness.seed(
        create_entry(
            seq=1, kind='known', text='the pool is shared', cite=QUEUE_CITE, quote=QUEUE_QUOTE
        ),
        create_entry(seq=2, kind='open', text='does the pool resize', diagram=FLOW),
        create_entry(seq=3, kind='open', text='an early guess', diagram=OLD_FLOW),
        create_entry(seq=4, kind='known', text='the guess was wrong', supersedes=('e3',)),
    )
    press_harness.seed_thread(
        'T1',
        create_entry(seq=1, kind='known', thread='T1', text='backoff doubles'),
        create_entry(seq=2, kind='open', thread='T1', text='is there jitter'),
    )
    press_harness.press.draw()
    return ScriptHarness(node=node, workdir=tmp_path, page=press_harness.pages.files['board.html'])


def list_hidden_refs(state: PageState) -> list[str]:
    return [entry['ref'] for entry in state['entries'] if entry['hidden']]


def list_hidden_sections(state: PageState) -> list[str]:
    return [section['title'] for section in state['sections'] if section['hidden']]


def list_open_sections(state: PageState) -> list[str]:
    return [section['title'] for section in state['sections'] if section['open']]


def list_drawn(state: PageState) -> list[bool]:
    return [diagram['drawn'] for diagram in state['diagrams']]


def list_drawn_sources(state: PageState) -> list[str]:
    return [source for run in state['runs'] for source in run]


class TestFilters:
    def test_the_script_marks_the_page_as_scripted(self, script: ScriptHarness) -> None:
        assert script.play()['root_classes'] == ['js']

    def test_a_kind_chip_hides_its_entries_and_the_section_left_empty(
        self, script: ScriptHarness
    ) -> None:
        state = script.play(click_chip('kind', 'known'))

        assert list_hidden_refs(state) == ['e1', 'e4', 'T1.e1']
        assert list_hidden_sections(state) == ['Known']
        assert [chip['value'] for chip in state['chips'] if not chip['pressed']] == ['known']

    def test_a_second_click_on_a_chip_shows_everything_again(self, script: ScriptHarness) -> None:
        state = script.play(click_chip('kind', 'known'), click_chip('kind', 'known'))

        assert list_hidden_refs(state) == []
        assert list_hidden_sections(state) == []
        assert all(chip['pressed'] for chip in state['chips'])

    def test_a_thread_chip_hides_that_thread_and_keeps_a_section_with_entries_left(
        self, script: ScriptHarness
    ) -> None:
        state = script.play(click_chip('thread', 'T1'))

        assert list_hidden_refs(state) == ['T1.e1', 'T1.e2']
        assert list_hidden_sections(state) == []

    def test_kind_and_thread_filters_add_up(self, script: ScriptHarness) -> None:
        state = script.play(click_chip('thread', ''), click_chip('kind', 'open'))

        assert [entry['ref'] for entry in state['entries'] if not entry['hidden']] == ['T1.e1']
        assert list_hidden_sections(state) == ['Open', RETIRED]

    def test_a_click_on_the_count_inside_a_chip_counts_as_the_chip(
        self, script: ScriptHarness
    ) -> None:
        state = script.play(click('.count'))

        assert state['chips'][0]['pressed'] is False


class TestFolding:
    def test_the_fold_button_closes_every_section_then_opens_them_all(
        self, script: ScriptHarness
    ) -> None:
        closed = script.play(click('[data-fold]'))
        opened = script.play(click('[data-fold]'), click('[data-fold]'))

        assert (list_open_sections(closed), closed['fold']) == ([], 'Expand all')
        assert len(list_open_sections(opened)) == len(opened['sections'])
        assert opened['fold'] == 'Collapse all'

    def test_closing_the_last_open_section_by_hand_relabels_the_button(
        self, script: ScriptHarness
    ) -> None:
        state = script.play(*(toggle(index, opened=False) for index in range(RETIRED_INDEX)))

        assert state['fold'] == 'Expand all'

    def test_opening_one_section_by_hand_relabels_the_button_back(
        self, script: ScriptHarness
    ) -> None:
        state = script.play(click('[data-fold]'), toggle(0, opened=True))

        assert (list_open_sections(state), state['fold']) == (['Known'], 'Collapse all')


class TestCopying:
    def test_copy_puts_the_citation_on_the_clipboard_and_says_so(
        self, script: ScriptHarness
    ) -> None:
        state = script.play(click('.copy'))

        assert state['clipboard'] == [QUEUE_CITE]
        assert state['status'] == f'Copied {QUEUE_CITE}'
        assert state['copied'] == [QUEUE_CITE]

    def test_the_copied_mark_goes_away_when_its_timer_runs(self, script: ScriptHarness) -> None:
        state = script.play(click('.copy'), run_timers())

        assert (state['copied'], state['timers']) == ([], 0)

    def test_a_ref_copies_the_entry_address(self, script: ScriptHarness) -> None:
        state = script.play(click('.ref', 2))

        assert state['clipboard'] == ['T1.e1']

    def test_a_denied_clipboard_falls_back_to_the_copy_command(self, script: ScriptHarness) -> None:
        state = script.play(deny_clipboard(), click('.copy'))

        assert (state['clipboard'], state['commands']) == ([], ['copy'])
        assert state['textareas'] == 0
        assert state['status'] == f'Copied {QUEUE_CITE}'


class TestLinks:
    def test_a_link_to_a_folded_section_opens_it(self, script: ScriptHarness) -> None:
        state = script.play(load(), navigate('section-retired'))

        assert RETIRED in list_open_sections(state)
        assert list_drawn(state) == [True, True, True]

    def test_a_link_to_nothing_on_the_page_opens_nothing(self, script: ScriptHarness) -> None:
        state = script.play(load(), navigate('section-elsewhere'))

        assert RETIRED not in list_open_sections(state)


class TestDiagrams:
    def test_load_draws_only_the_diagrams_outside_a_closed_section(
        self, script: ScriptHarness
    ) -> None:
        state = script.play(load())

        assert list_drawn(state) == [True, True, False]
        assert state['diagrams'][2]['text'] == OLD_FLOW
        assert state['runs'][0][0] == FLOW

    def test_diagrams_are_drawn_strict_and_never_on_their_own(self, script: ScriptHarness) -> None:
        (theme,) = script.play(load())['themes']

        assert (theme['security'], theme['starts_on_load']) == ('strict', False)
        assert (theme['dark'], theme['ink']) == (False, 'light--ink')

    def test_opening_a_section_draws_its_diagram_once(self, script: ScriptHarness) -> None:
        state = script.play(
            load(),
            toggle(RETIRED_INDEX, opened=True),
            toggle(RETIRED_INDEX, opened=False),
            toggle(RETIRED_INDEX, opened=True),
        )

        assert list_drawn(state) == [True, True, True]
        assert state['runs'][1:] == [[OLD_FLOW]]

    def test_expand_all_draws_the_diagrams_it_reveals(self, script: ScriptHarness) -> None:
        state = script.play(load(), click('[data-fold]'), click('[data-fold]'))

        assert list_drawn(state) == [True, True, True]
        assert list_drawn_sources(state).count(OLD_FLOW) == 1

    def test_a_theme_choice_redraws_the_drawn_diagrams_from_their_source(
        self, script: ScriptHarness
    ) -> None:
        state = script.play(load(), choose_theme('dark'))

        assert [theme['ink'] for theme in state['themes']] == ['light--ink', 'dark--ink']
        assert state['runs'][1] == state['runs'][0]
        assert state['diagrams'][0]['text'] == f'drawn in dark--ink: {FLOW}'
        assert list_drawn(state) == [True, True, False]

    def test_a_system_scheme_change_redraws_the_diagrams(self, script: ScriptHarness) -> None:
        state = script.play(load(), switch_scheme(dark=True))

        assert [theme['dark'] for theme in state['themes']] == [False, True]
        assert state['diagrams'][0]['text'] == f'drawn in dark--ink: {FLOW}'

    def test_a_chosen_light_theme_wins_over_a_dark_system(self, script: ScriptHarness) -> None:
        state = script.play(switch_scheme(dark=True), load(), choose_theme('light'))

        assert [theme['dark'] for theme in state['themes']] == [True, False]
        assert state['diagrams'][0]['text'] == f'drawn in light--ink: {FLOW}'

    def test_a_diagram_opened_after_a_theme_change_is_drawn_in_the_new_theme(
        self, script: ScriptHarness
    ) -> None:
        state = script.play(load(), choose_theme('dark'), toggle(RETIRED_INDEX, opened=True))

        assert state['diagrams'][2]['text'] == f'drawn in dark--ink: {OLD_FLOW}'

    def test_without_the_diagram_library_the_page_keeps_the_source_and_the_filters(
        self, script: ScriptHarness
    ) -> None:
        state = script.play(
            load(), click_chip('kind', 'known'), choose_theme('dark'), mermaid=False
        )

        assert (state['runs'], list_drawn(state)) == ([], [False, False, False])
        assert state['diagrams'][0]['text'] == FLOW
        assert list_hidden_sections(state) == ['Known']
