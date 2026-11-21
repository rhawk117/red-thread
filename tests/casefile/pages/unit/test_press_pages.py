"""Press: board.html and the HTML twin of a lens output, over the in-memory ledger."""

from typing import TYPE_CHECKING

import pytest
from msgspec.structs import replace
from red_thread_casefile.lenses import Plan

from tests.casefile.ledger.builders import create_case, create_entry
from tests.casefile.lenses.builders import create_numbered_entries, seed_flag_scenario
from tests.casefile.lenses.cases import QUEUE_CITE, QUEUE_QUOTE, flag_params, lens_name_params
from tests.casefile.lenses.reading import list_all_refs
from tests.casefile.pages.html_reading import (
    find_tags,
    list_claims,
    list_flags,
    list_item_refs,
    list_mermaid,
    list_section_titles,
    list_tag_names,
)
from tests.casefile.pages.promises import assert_page_holds_only_its_own_markup

if TYPE_CHECKING:
    from red_thread_casefile.lenses import LensName

    from tests.casefile.lenses.builders import PressHarness
    from tests.casefile.lenses.cases import FlagScenario

SCRIPT = '<script>alert(1)</script>'
DIAGRAM = 'flowchart TD\n  A["one"] --> B["two"]\n  B --> C'


def lens_name_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('lens', lens_name_params())


def flag_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('scenario', flag_params())


class TestBoardPage:
    def test_the_board_page_is_written_as_board_html_and_nothing_else(
        self, press_harness: PressHarness
    ) -> None:
        written = press_harness.press.draw()

        assert written.name == 'board.html'
        assert set(press_harness.snapshot()) == {'board.html'}

    def test_the_board_page_shows_every_live_entry_beyond_the_text_boards_cap(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(
            *create_numbered_entries('known', 12),
            *create_numbered_entries('open', 9, start=13),
            create_entry(seq=22, kind='open', text='replacement', supersedes=('e1', 'e13')),
        )

        press_harness.press.draw()

        refs = list_item_refs(press_harness.pages.files['board.html'])
        live = {f'e{number}' for number in range(1, 23)} - {'e1', 'e13'}
        assert sorted(refs) == sorted(live)

    def test_a_retired_entry_is_not_on_the_board_page(self, press_harness: PressHarness) -> None:
        press_harness.seed(
            create_entry(seq=1, kind='open', text='the stale question'),
            create_entry(seq=2, kind='open', text='the fresh question', supersedes=('e1',)),
        )

        press_harness.press.draw()

        page = press_harness.pages.files['board.html']
        assert list_item_refs(page) == ['e2']
        assert list_claims(page) == ['the fresh question']

    def test_an_empty_ledger_gives_a_page_with_no_entry(self, press_harness: PressHarness) -> None:
        press_harness.press.draw()

        assert list_item_refs(press_harness.pages.files['board.html']) == []

    @flag_cases()
    def test_the_board_page_carries_the_flags_of_each_entry(
        self, press_harness: PressHarness, scenario: FlagScenario
    ) -> None:
        seed_flag_scenario(press_harness, scenario)

        press_harness.press.draw()

        assert list_flags(press_harness.pages.files['board.html']) == list(scenario.flags)

    def test_ledger_text_and_the_case_target_cannot_add_elements(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.frame(replace(create_case(), target=SCRIPT))
        press_harness.seed(
            create_entry(
                seq=1,
                kind='known',
                text=SCRIPT,
                cite=f'https://example.invalid/"{SCRIPT}',
                rests_on=SCRIPT,
                source=SCRIPT,
            )
        )

        press_harness.press.draw()

        page = press_harness.pages.files['board.html']
        assert_page_holds_only_its_own_markup(page)
        assert page.lower().count('<script') == 3

    def test_board_page_keeps_the_page_promise(self, press_harness: PressHarness) -> None:
        press_harness.seed(
            create_entry(seq=1, kind='known', text='a claim', cite=QUEUE_CITE, quote=QUEUE_QUOTE)
        )

        press_harness.press.draw()

        page = press_harness.pages.files['board.html']
        assert_page_holds_only_its_own_markup(page)
        assert 'link' not in list_tag_names(page)

    def test_the_board_page_ends_in_a_map_section_drawing_every_entry_retired_ones_too(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(
            create_entry(seq=1, kind='open', text='the stale question'),
            create_entry(seq=2, kind='open', text='the fresh question', supersedes=('e1',)),
        )
        press_harness.seed_thread('T1', create_entry(seq=1, thread='T1', kind='known', text='deep'))

        press_harness.press.draw()

        page = press_harness.pages.files['board.html']
        assert list_section_titles(page)[-1] == 'Map'
        (drawn,) = list_mermaid(page)
        assert drawn.startswith('flowchart TD')
        assert 'e1 open: the stale question' in drawn
        assert 'e2 open: the fresh question' in drawn
        assert 'T1.e1 known: deep' in drawn
        assert 'retires' in drawn

    def test_an_empty_ledger_draws_no_map(self, press_harness: PressHarness) -> None:
        press_harness.press.draw()

        page = press_harness.pages.files['board.html']
        assert list_section_titles(page) == []
        assert list_mermaid(page) == []

    def test_an_entry_diagram_is_drawn_before_the_map_and_never_in_the_text_board(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(create_entry(seq=1, kind='known', text='a claim', diagram=DIAGRAM))

        press_harness.press.draw()

        diagram, drawn = list_mermaid(press_harness.pages.files['board.html'])
        assert diagram == DIAGRAM
        assert drawn.startswith('flowchart TD')


class TestLensPage:
    @lens_name_cases()
    def test_the_page_is_written_beside_the_markdown_when_asked_for(
        self, press_harness: PressHarness, lens: LensName
    ) -> None:
        exported = press_harness.export(lens, html=True)

        assert [path.name for path in exported.paths] == [f'{lens}.md', f'{lens}.html']
        assert set(press_harness.snapshot()) == {f'out/{lens}.md', f'out/{lens}.html'}

    def test_no_page_is_written_unless_asked_for(self, press_harness: PressHarness) -> None:
        exported = press_harness.export('brief')

        assert [path.name for path in exported.paths] == ['brief.md']
        assert set(press_harness.snapshot()) == {'out/brief.md'}

    def test_page_and_markdown_list_the_same_entries(self, press_harness: PressHarness) -> None:
        press_harness.seed(
            *create_numbered_entries('known', 3),
            *create_numbered_entries('open', 2, start=4),
        )

        press_harness.export('brief', Plan(include=('e3', 'e1', 'e5')), html=True)

        markdown_refs = list_all_refs(press_harness.read_markdown('brief'))
        assert list_item_refs(press_harness.read_page('brief')) == markdown_refs
        assert markdown_refs == ['e3', 'e1', 'e5']

    @flag_cases()
    def test_the_page_carries_the_flags_of_each_entry(
        self, press_harness: PressHarness, scenario: FlagScenario
    ) -> None:
        seed_flag_scenario(press_harness, scenario)

        press_harness.export('brief', html=True)

        assert list_flags(press_harness.read_page('brief')) == list(scenario.flags)

    def test_the_urgency_label_is_shown_on_the_page(self, press_harness: PressHarness) -> None:
        press_harness.seed(*create_numbered_entries('open', 2))

        press_harness.export('brief', Plan(blocking=('e2',)), html=True)

        page = press_harness.read_page('brief')
        assert 'not blocking' in page
        assert page.count('blocking') == 2

    def test_plan_title_goal_and_entries_cannot_add_elements(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(
            create_entry(seq=1, kind='open', text=SCRIPT, rests_on=SCRIPT, cite=SCRIPT)
        )

        press_harness.export('brief', Plan(title=SCRIPT, goal=SCRIPT), html=True)

        page = press_harness.read_page('brief')
        assert_page_holds_only_its_own_markup(page)
        assert page.lower().count('<script') == 3

    def test_a_lens_page_draws_an_entry_diagram_and_no_map(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(create_entry(seq=1, kind='open', text='a question', diagram=DIAGRAM))

        press_harness.export('brief', html=True)

        page = press_harness.read_page('brief')
        assert list_mermaid(page) == [DIAGRAM]
        assert 'Map' not in list_section_titles(page)

    def test_a_diagram_is_not_in_the_markdown_output(self, press_harness: PressHarness) -> None:
        press_harness.seed(create_entry(seq=1, kind='open', text='a question', diagram=DIAGRAM))

        press_harness.export('brief', html=True)

        assert 'flowchart' not in press_harness.read_markdown('brief')
        assert 'a question' in press_harness.read_markdown('brief')

    def test_a_url_cite_is_a_link_and_a_path_cite_is_not(self, press_harness: PressHarness) -> None:
        press_harness.seed(
            create_entry(seq=1, kind='known', text='a', cite='https://example.invalid/a'),
            create_entry(seq=2, kind='known', text='b', cite=QUEUE_CITE, quote=QUEUE_QUOTE),
        )

        press_harness.export('brief', html=True)

        links = find_tags(press_harness.read_page('brief'), 'a')
        assert [link['href'] for link in links] == ['https://example.invalid/a']

    def test_a_url_cite_with_a_quote_cannot_break_out_of_the_href(
        self, press_harness: PressHarness
    ) -> None:
        cite = 'https://example.invalid/x" onmouseover="alert(1)'
        press_harness.seed(create_entry(seq=1, kind='known', text='a', cite=cite))

        press_harness.export('brief', html=True)

        (link,) = find_tags(press_harness.read_page('brief'), 'a')
        assert link['href'] == cite
        assert set(link) == {'href', 'rel'}
