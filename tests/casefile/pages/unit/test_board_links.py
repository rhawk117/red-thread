"""The board's links: an anchor per entry, columns and its words."""

from html import escape
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.packaged import load_wording

from tests.casefile.ledger.builders import create_entry
from tests.casefile.pages.html_reading import find_entries, list_item_refs

if TYPE_CHECKING:
    from tests.casefile.lenses.builders import PressHarness


def draw_board(harness: PressHarness) -> str:
    harness.press.draw()
    return harness.pages.files['board.html']


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
        assert all(escape(term.word) in page for term in load_wording().terms)
