"""A page_url in the frontmatter: the board, the board page and the pointers show it."""

from typing import TYPE_CHECKING

import pytest
from msgspec.structs import replace

from tests.casefile.ledger.builders import PAGE_URL, create_case, create_entry
from tests.casefile.lenses.cases import lens_name_params
from tests.casefile.lenses.reading import list_section_lines
from tests.casefile.pages.html_reading import list_facts

if TYPE_CHECKING:
    from red_thread_casefile.lenses import LensName

    from tests.casefile.lenses.builders import PressHarness


def lens_name_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('lens', lens_name_params())


def seed_question(harness: PressHarness) -> PressHarness:
    harness.seed(create_entry(seq=1, kind='open', text='who owns the queue'))
    return harness


class TestPageUrlIsShown:
    @pytest.fixture
    def unpublished(self, press_harness: PressHarness) -> PressHarness:
        return seed_question(press_harness)

    @pytest.fixture
    def published(self, press_harness: PressHarness) -> PressHarness:
        press_harness.frame(replace(create_case(), page_url=PAGE_URL))
        return seed_question(press_harness)

    def test_the_board_shows_the_link(self, published: PressHarness) -> None:
        assert f'Page: {PAGE_URL}' in published.case.casefile.show().splitlines()

    def test_the_board_has_no_page_line_without_a_link(self, unpublished: PressHarness) -> None:
        assert 'Page:' not in unpublished.case.casefile.show()

    @lens_name_cases()
    def test_the_pointers_show_the_board_link(
        self, published: PressHarness, lens: LensName
    ) -> None:
        text = published.export_markdown(lens)

        assert f'- Board: {PAGE_URL}' in list_section_lines(text, 'Pointers')

    @lens_name_cases()
    def test_the_pointers_have_no_board_line_without_a_link(
        self, unpublished: PressHarness, lens: LensName
    ) -> None:
        text = unpublished.export_markdown(lens)

        assert not any(line.startswith('- Board:') for line in list_section_lines(text, 'Pointers'))

    def test_the_board_page_shows_the_link(self, published: PressHarness) -> None:
        published.press.draw()
        page = published.pages.files['board.html']

        (fact,) = [fact for fact in list_facts(page) if fact.label == 'Page']
        assert (fact.value, fact.link) == (PAGE_URL, PAGE_URL)
