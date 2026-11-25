"""Press: board.html and the HTML twin of a lens output, over the in-memory ledger."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.lenses import Plan
from red_thread_casefile.views import describe_kind

from tests.casefile.ledger.builders import create_entry
from tests.casefile.lenses.builders import create_numbered_entries, export, seed_flag_scenario
from tests.casefile.lenses.cases import QUEUE_CITE, QUEUE_QUOTE, flag_params, lens_name_params
from tests.casefile.lenses.reading import list_all_refs
from tests.casefile.pages.builders import DIAGRAM, SCRIPT
from tests.casefile.pages.html_reading import (
    find_tags,
    list_item_refs,
    list_mermaid,
    list_section_titles,
    list_sections,
)
from tests.casefile.pages.promises import (
    assert_page_holds_only_its_own_markup,
    assert_page_shows_flags,
)

if TYPE_CHECKING:
    from red_thread_casefile.lenses import LensName

    from tests.casefile.lenses.builders import PressHarness
    from tests.casefile.lenses.cases import FlagScenario


def lens_name_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('lens', lens_name_params())


def flag_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('scenario', flag_params())


class TestLensPage:
    @lens_name_cases()
    def test_the_page_is_written_beside_the_markdown_when_asked_for(
        self, press_harness: PressHarness, lens: LensName
    ) -> None:
        exported = export(press_harness, lens, html=True)

        assert [path.name for path in exported.paths] == [f'{lens}.md', f'{lens}.html']
        assert set(press_harness.snapshot()) == {f'out/{lens}.md', f'out/{lens}.html'}

    def test_no_page_is_written_unless_asked_for(self, press_harness: PressHarness) -> None:
        exported = export(press_harness, 'brief')

        assert [path.name for path in exported.paths] == ['brief.md']
        assert set(press_harness.snapshot()) == {'out/brief.md'}

    def test_page_and_markdown_list_the_same_entries(self, press_harness: PressHarness) -> None:
        press_harness.seed(
            *create_numbered_entries('known', 3),
            *create_numbered_entries('open', 2, start=4),
        )

        export(press_harness, 'brief', Plan(include=('e3', 'e1', 'e5')), html=True)

        markdown_refs = list_all_refs(press_harness.read_markdown('brief'))
        assert list_item_refs(press_harness.read_page('brief')) == markdown_refs
        assert markdown_refs == ['e3', 'e1', 'e5']

    @flag_cases()
    def test_the_page_carries_the_flags_of_each_entry(
        self, press_harness: PressHarness, scenario: FlagScenario
    ) -> None:
        seed_flag_scenario(press_harness, scenario)

        export(press_harness, 'brief', html=True)

        assert_page_shows_flags(press_harness.read_page('brief'), scenario.flags)

    def test_the_urgency_label_is_shown_on_the_page(self, press_harness: PressHarness) -> None:
        press_harness.seed(*create_numbered_entries('open', 2))

        export(press_harness, 'brief', Plan(blocking=('e2',)), html=True)

        page = press_harness.read_page('brief')
        assert 'not blocking' in page
        assert page.count('blocking') == 2

    def test_plan_title_goal_and_entries_cannot_add_elements(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(
            create_entry(seq=1, kind='open', text=SCRIPT, rests_on=SCRIPT, cite=SCRIPT)
        )

        export(press_harness, 'brief', Plan(title=SCRIPT, goal=SCRIPT), html=True)

        page = press_harness.read_page('brief')
        assert_page_holds_only_its_own_markup(page)
        assert page.lower().count('<script') == 3

    def test_a_lens_page_draws_an_entry_diagram_and_no_map(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(create_entry(seq=1, kind='open', text='a question', diagram=DIAGRAM))

        export(press_harness, 'brief', html=True)

        page = press_harness.read_page('brief')
        assert list_mermaid(page) == [DIAGRAM]
        assert 'Map' not in list_section_titles(page)

    def test_a_diagram_is_not_in_the_markdown_output(self, press_harness: PressHarness) -> None:
        press_harness.seed(create_entry(seq=1, kind='open', text='a question', diagram=DIAGRAM))

        export(press_harness, 'brief', html=True)

        assert 'flowchart' not in press_harness.read_markdown('brief')
        assert 'a question' in press_harness.read_markdown('brief')

    def test_a_url_cite_is_a_link_and_a_path_cite_is_not(self, press_harness: PressHarness) -> None:
        press_harness.seed(
            create_entry(seq=1, kind='known', text='a', cite='https://example.invalid/a'),
            create_entry(seq=2, kind='known', text='b', cite=QUEUE_CITE, quote=QUEUE_QUOTE),
        )

        export(press_harness, 'brief', html=True)

        links = find_tags(press_harness.read_page('brief'), 'a')
        assert [link['href'] for link in links] == ['https://example.invalid/a']

    def test_a_url_cite_with_a_quote_cannot_break_out_of_the_href(
        self, press_harness: PressHarness
    ) -> None:
        cite = 'https://example.invalid/x" onmouseover="alert(1)'
        press_harness.seed(create_entry(seq=1, kind='known', text='a', cite=cite))

        export(press_harness, 'brief', html=True)

        (link,) = find_tags(press_harness.read_page('brief'), 'a')
        assert link['href'] == cite
        assert set(link) == {'href', 'rel'}


class TestLensSections:
    def test_a_section_made_from_a_kind_carries_the_kind_and_its_note(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(*create_numbered_entries('known', 2))

        export(press_harness, 'brief', Plan(include=('e1', 'e2')), html=True)

        sections = {
            section.title: section for section in list_sections(press_harness.read_page('brief'))
        }
        assert sections['Constraints'].attributes.get('data-kind') == 'known'
        assert sections['Constraints'].note == describe_kind('known')

    def test_a_fixed_part_carries_no_kind_and_no_note(self, press_harness: PressHarness) -> None:
        press_harness.seed(*create_numbered_entries('known', 2))

        export(press_harness, 'brief', Plan(include=('e1', 'e2')), html=True)

        sections = {
            section.title: section for section in list_sections(press_harness.read_page('brief'))
        }
        assert 'data-kind' not in sections['Goal'].attributes
        assert sections['Goal'].note is None
