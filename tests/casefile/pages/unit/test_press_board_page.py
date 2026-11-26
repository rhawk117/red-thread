"""Press: board.html over the in-memory ledger, with facts, sections, badges and retired fold."""

from typing import TYPE_CHECKING

import pytest
from msgspec.structs import replace

from tests.casefile.ledger.builders import create_case, create_entry
from tests.casefile.lenses.builders import create_numbered_entries, seed_flag_scenario
from tests.casefile.lenses.cases import QUEUE_CITE, QUEUE_QUOTE, flag_params
from tests.casefile.pages.builders import DIAGRAM, SCRIPT
from tests.casefile.pages.html_reading import (
    find_tags,
    list_chip_groups,
    list_cited_quotes,
    list_claim_markup,
    list_facts,
    list_item_refs,
    list_mermaid,
    list_note_rows,
    list_section_titles,
    list_sections,
    list_spans,
    list_tag_names,
)
from tests.casefile.pages.promises import (
    assert_page_holds_only_its_own_markup,
    assert_page_shows_flags,
)

if TYPE_CHECKING:
    from tests.casefile.lenses.builders import PressHarness
    from tests.casefile.lenses.cases import FlagScenario

PAGE_URL = 'https://claude.ai/artifact/retry-queue'
FACT_LABELS = [
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
RETIRED = 'Retired'


def draw_board(harness: PressHarness) -> str:
    harness.press.draw()
    return harness.pages.files['board.html']


def flag_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('scenario', flag_params())


class TestBoardPageFacts:
    def test_the_board_page_is_written_as_board_html_and_nothing_else(
        self, press_harness: PressHarness
    ) -> None:
        written = press_harness.press.draw()

        assert written.name == 'board.html'
        assert set(press_harness.snapshot()) == {'board.html'}

    def test_an_empty_ledger_gives_facts_and_no_entry_no_map_no_toolbar(
        self, press_harness: PressHarness
    ) -> None:
        page = draw_board(press_harness)

        assert list_item_refs(page) == []
        assert list_section_titles(page) == []
        assert list_mermaid(page) == []
        assert find_tags(page, 'nav') == []
        assert [fact.label for fact in list_facts(page)] == FACT_LABELS

    def test_the_header_shows_the_case_line_and_the_facts_in_order(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(*create_numbered_entries('open', 2))

        page = draw_board(press_harness)

        facts = {fact.label: fact for fact in list_facts(page)}
        assert [fact.label for fact in list_facts(page)] == FACT_LABELS
        assert facts['Bar'].value == create_case().bar
        assert facts['Entries'].value == '2 live, 0 retired'
        assert facts['Created'].value == '2026-11-21'
        assert facts['Commit'].value == '1111111'
        assert {label for label, fact in facts.items() if fact.wide} == {'Bar', 'Citations'}
        assert 'Case 20261121-retry-queue-slowdown' in page

    def test_a_recorded_page_link_is_a_last_wide_fact_that_links(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.frame(replace(create_case(), page_url=PAGE_URL))

        facts = list_facts(draw_board(press_harness))

        assert [fact.label for fact in facts] == [*FACT_LABELS, 'Page']
        assert (facts[-1].wide, facts[-1].link, facts[-1].value) == (True, PAGE_URL, PAGE_URL)

    def test_the_board_page_keeps_the_page_promise(self, press_harness: PressHarness) -> None:
        press_harness.seed(
            create_entry(seq=1, kind='known', text='a claim', cite=QUEUE_CITE, quote=QUEUE_QUOTE)
        )

        page = draw_board(press_harness)

        assert_page_holds_only_its_own_markup(page)
        assert 'link' not in list_tag_names(page)


class TestBoardPageSections:
    def test_the_sections_show_every_live_entry_beyond_the_text_boards_cap(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(
            *create_numbered_entries('known', 12),
            *create_numbered_entries('open', 9, start=13),
            create_entry(seq=22, kind='open', text='replacement', supersedes=('e1', 'e13')),
        )

        page = draw_board(press_harness)

        sections = [section for section in list_sections(page) if section.title != RETIRED]
        shown = [ref for section in sections for ref in list_item_refs(section.body)]
        live = {f'e{number}' for number in range(1, 23)} - {'e1', 'e13'}
        assert sorted(shown) == sorted(live)

    def test_a_retired_entry_sits_in_the_last_fold_closed_and_names_who_retired_it(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(
            create_entry(seq=1, kind='open', text='the stale question'),
            create_entry(seq=2, kind='open', text='the fresh question', supersedes=('e1',)),
        )

        page = draw_board(press_harness)

        *others, last = list_sections(page)
        entry_sections = [section for section in others if section.title != 'Map']
        assert last.title == RETIRED
        assert 'open' not in last.attributes
        assert list_item_refs(last.body) == ['e1']
        assert ('', 'retired by e2') in list_note_rows(last.body)[0]
        assert all('retired by' not in str(list_note_rows(s.body)) for s in entry_sections)
        assert 'the stale question' not in ''.join(s.body for s in entry_sections)

    def test_no_retired_entry_leaves_no_retired_fold(self, press_harness: PressHarness) -> None:
        press_harness.seed(*create_numbered_entries('open', 2))

        page = draw_board(press_harness)

        assert RETIRED not in list_section_titles(page)

    def test_the_chips_count_live_entries_only(self, press_harness: PressHarness) -> None:
        press_harness.seed(
            create_entry(seq=1, kind='open', text='stale'),
            create_entry(seq=2, kind='open', text='fresh', supersedes=('e1',)),
            create_entry(seq=3, kind='known', text='a', cite=QUEUE_CITE),
        )

        groups = list_chip_groups(draw_board(press_harness))

        (kinds,) = [group for group in groups if group[0].group == 'kind']
        assert [(chip.value, chip.count) for chip in kinds] == [('known', 1), ('open', 1)]

    def test_the_page_ends_with_the_map_then_the_retired_fold(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(
            create_entry(seq=1, kind='open', text='the stale question'),
            create_entry(seq=2, kind='open', text='the fresh question', supersedes=('e1',)),
        )
        press_harness.seed_thread('T1', create_entry(seq=1, thread='T1', kind='known', text='deep'))

        page = draw_board(press_harness)

        assert list_section_titles(page)[-2:] == ['Map', RETIRED]
        assert 'e1 open: the stale question' in list_mermaid(page)[-1]

    def test_without_a_retired_entry_the_map_is_last(self, press_harness: PressHarness) -> None:
        press_harness.seed(*create_numbered_entries('open', 2))

        assert list_section_titles(draw_board(press_harness))[-1] == 'Map'

    def test_an_entry_diagram_is_drawn_before_the_map(self, press_harness: PressHarness) -> None:
        press_harness.seed(create_entry(seq=1, kind='known', text='a claim', diagram=DIAGRAM))

        diagram, drawn = list_mermaid(draw_board(press_harness))

        assert diagram == DIAGRAM
        assert drawn.startswith('flowchart TD')


class TestBoardPageEntries:
    @flag_cases()
    def test_the_board_page_carries_the_flags_and_state_badge_of_each_entry(
        self, press_harness: PressHarness, scenario: FlagScenario
    ) -> None:
        seed_flag_scenario(press_harness, scenario)

        assert_page_shows_flags(draw_board(press_harness), scenario.flags)

    def test_an_unknown_verdict_is_a_badge_before_the_text_and_a_known_has_none(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(
            create_entry(seq=1, kind='open', text='maybe', verdict='INFERRED'),
            create_entry(seq=2, kind='known', text='sure', verdict='VERIFIED', cite=QUEUE_CITE),
        )

        page = draw_board(press_harness)

        (badge,) = list_spans(page, 'verdict')
        assert (badge.body, badge.attributes['data-verdict']) == ('INFERRED', 'INFERRED')
        markup = list_claim_markup(page)
        assert markup[1].startswith(
            '<span class="verdict" data-verdict="INFERRED">INFERRED</span> '
        )
        assert 'INFERRED:' not in page
        assert 'VERIFIED' not in markup[0]

    def test_a_cited_entry_shows_its_quote_after_the_cite_and_its_round_and_day(
        self, press_harness: PressHarness
    ) -> None:
        entry = create_entry(seq=1, kind='known', text='a', cite=QUEUE_CITE, quote=QUEUE_QUOTE)
        press_harness.seed(entry)

        page = draw_board(press_harness)

        assert list_cited_quotes(page) == [QUEUE_QUOTE]
        assert list_note_rows(page)[0][:2] == [('stamp', 'round 1'), ('stamp', '2026-11-21')]

    def test_each_section_carries_its_kind_its_count_and_its_note(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.seed(
            *create_numbered_entries('open', 3), *create_numbered_entries('next', 1, start=4)
        )

        sections = list_sections(draw_board(press_harness))

        assert [(s.title, s.count, s.attributes['data-kind']) for s in sections[:2]] == [
            ('Open', 3, 'open'),
            ('Next', 1, 'next'),
        ]
        assert all(section.note for section in sections)

    def test_ledger_text_and_the_case_fields_cannot_add_elements(
        self, press_harness: PressHarness
    ) -> None:
        press_harness.frame(replace(create_case(), target=SCRIPT, bar=SCRIPT))
        press_harness.seed(
            create_entry(
                seq=1,
                kind='known',
                text=SCRIPT,
                cite=f'https://example.invalid/"{SCRIPT}',
                rests_on=SCRIPT,
                source=SCRIPT,
            ),
            create_entry(seq=2, kind='known', text=SCRIPT, cite=QUEUE_CITE, quote=SCRIPT),
        )

        page = draw_board(press_harness)

        assert_page_holds_only_its_own_markup(page)
        assert page.lower().count('<script') == 3
