"""The board's links: the plans that cite the case, an anchor per entry, columns and its words."""

from dataclasses import replace
from html import escape
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.terms import BOARD_TERMS
from red_thread_core.mentions import MemoryMentionShelf, PlanMention

from tests.casefile.ledger.builders import create_case, create_entry
from tests.casefile.pages.html_reading import find_entries, list_facts, list_item_refs

if TYPE_CHECKING:
    from tests.casefile.lenses.builders import PressHarness

CUT = PlanMention(id='20261126-cut', title='Cut the work', cases=(create_case().id,))
SHIP = PlanMention(id='20261127-ship', title='Ship it', cases=(create_case().id,))
ELSEWHERE = PlanMention(id='20261128-other', title='Other work', cases=('another-case',))


def draw_board(harness: PressHarness) -> str:
    harness.press.draw()
    return harness.pages.files['board.html']


def cite_case(harness: PressHarness, *mentions: PlanMention) -> PressHarness:
    shelf = MemoryMentionShelf(mentions=mentions)
    return replace(harness, press=replace(harness.press, mentions=shelf))


class TestBoardPlans:
    def test_each_plan_that_cites_the_case_is_a_link_to_its_page(
        self, press_harness: PressHarness
    ) -> None:
        page = draw_board(cite_case(press_harness, CUT, ELSEWHERE))

        plans = list_facts(page)[-1]
        assert (plans.label, plans.value, plans.wide) == ('Plans', 'Cut the work', True)
        assert plans.link == '../plans/20261126-cut/plan.html'

    def test_several_plans_are_listed_in_order(self, press_harness: PressHarness) -> None:
        page = draw_board(cite_case(press_harness, CUT, SHIP))

        assert list_facts(page)[-1].value == 'Cut the work, Ship it'
        assert 'href="../plans/20261127-ship/plan.html"' in page

    def test_a_case_no_plan_cites_has_no_plans_fact(self, press_harness: PressHarness) -> None:
        page = draw_board(cite_case(press_harness, ELSEWHERE))

        assert 'Plans' not in [fact.label for fact in list_facts(page)]


class TestBoardLayout:
    @pytest.fixture
    def seeded(self, press_harness: PressHarness) -> PressHarness:
        press_harness.seed(
            create_entry(seq=1, kind='known', text='the pool is shared'),
            create_entry(seq=2, kind='open', text='does the pool resize'),
            create_entry(seq=3, kind='open', text='an early guess'),
            create_entry(seq=4, kind='known', text='the guess was wrong', supersedes=('e3',)),
        )
        return press_harness

    def test_each_entry_is_an_anchor_named_by_its_ref(self, seeded: PressHarness) -> None:
        page = draw_board(seeded)

        assert [entry['id'] for entry in find_entries(page)] == list_item_refs(page)

    def test_the_kind_sections_sit_side_by_side_and_the_retired_fold_does_not(
        self, seeded: PressHarness
    ) -> None:
        page = draw_board(seeded)

        before_map = page.split('<details class="section" id="section-map"')[0]
        columns = before_map.split('<div class="columns">')[1]
        assert page.count('<div class="columns">') == 1
        assert columns.rstrip().endswith('</div>')
        assert 'id="section-known"' in columns
        assert 'id="section-open"' in columns
        assert 'id="section-retired"' not in columns

    def test_the_board_explains_each_word_it_uses(self, seeded: PressHarness) -> None:
        page = draw_board(seeded)

        assert '<details class="terms">' in page
        assert all(escape(term.word) in page for term in BOARD_TERMS)
