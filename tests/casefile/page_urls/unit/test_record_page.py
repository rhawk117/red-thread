"""Press.record_page: the link is stored on the case, and the board and the pointers show it."""

from typing import TYPE_CHECKING

import pytest
from msgspec.structs import replace
from red_thread_casefile.domain import Capabilities
from red_thread_casefile.errors import InvalidPageUrlError

from tests.casefile.ledger.builders import PAGE_URL, create_case, create_entry
from tests.casefile.lenses.cases import lens_name_params
from tests.casefile.lenses.reading import list_section_lines
from tests.casefile.pages.html_reading import list_facts

if TYPE_CHECKING:
    from red_thread_casefile.lenses import LensName

    from tests.casefile.lenses.builders import PressHarness

OTHER_URL = 'https://example.invalid/board/2'


def lens_name_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('lens', lens_name_params())


class TestRecordPage:
    @pytest.fixture
    def harness(self, press_harness: PressHarness) -> PressHarness:
        press_harness.frame(
            replace(
                create_case(),
                publish=True,
                capabilities=Capabilities(languages=('Python', 'Go')),
            )
        )
        press_harness.seed(create_entry(seq=1, kind='open', text='who owns the queue'))
        return press_harness

    def test_the_link_is_stored_on_the_case_and_returned(self, harness: PressHarness) -> None:
        returned = harness.press.record_page(PAGE_URL)

        assert returned.page_url == PAGE_URL
        assert harness.case.repository.read_case() == returned

    def test_every_other_field_of_the_case_is_left_as_it_was(self, harness: PressHarness) -> None:
        before = harness.case.repository.read_case()

        harness.press.record_page(PAGE_URL)

        after = harness.case.repository.read_case()
        assert replace(after, page_url=before.page_url) == before

    def test_the_ledger_is_left_as_it_was(self, harness: PressHarness) -> None:
        before = harness.case.entries

        harness.press.record_page(PAGE_URL)

        assert harness.case.entries == before

    def test_a_second_link_replaces_the_first(self, harness: PressHarness) -> None:
        harness.press.record_page(PAGE_URL)

        harness.press.record_page(OTHER_URL)

        assert harness.case.repository.read_case().page_url == OTHER_URL

    @pytest.mark.parametrize(
        'url',
        [
            pytest.param('http://example.invalid/b', id='http'),
            pytest.param('https://example.invalid/a b', id='whitespace'),
            pytest.param('', id='empty'),
        ],
    )
    def test_a_rejected_link_raises_and_leaves_the_case_as_it_was(
        self, harness: PressHarness, url: str
    ) -> None:
        harness.press.record_page(PAGE_URL)
        before = harness.case.repository.read_case()

        with pytest.raises(InvalidPageUrlError) as raised:
            harness.press.record_page(url)

        assert raised.value.url == url
        assert harness.case.repository.read_case() == before


class TestRecordedPageIsShown:
    @pytest.fixture
    def harness(self, press_harness: PressHarness) -> PressHarness:
        press_harness.seed(create_entry(seq=1, kind='open', text='who owns the queue'))
        return press_harness

    def test_the_board_shows_the_link_once_it_is_recorded(self, harness: PressHarness) -> None:
        harness.press.record_page(PAGE_URL)

        assert f'Page: {PAGE_URL}' in harness.case.casefile.show().splitlines()

    def test_the_board_has_no_page_line_before_a_link_is_recorded(
        self, harness: PressHarness
    ) -> None:
        assert 'Page:' not in harness.case.casefile.show()

    @lens_name_cases()
    def test_the_pointers_show_the_board_link_once_it_is_recorded(
        self, harness: PressHarness, lens: LensName
    ) -> None:
        harness.press.record_page(PAGE_URL)

        text = harness.export_markdown(lens)

        assert f'- Board: {PAGE_URL}' in list_section_lines(text, 'Pointers')

    @lens_name_cases()
    def test_the_pointers_have_no_board_line_before_a_link_is_recorded(
        self, harness: PressHarness, lens: LensName
    ) -> None:
        text = harness.export_markdown(lens)

        assert not any(line.startswith('- Board:') for line in list_section_lines(text, 'Pointers'))

    def test_the_pointers_show_the_latest_link_only(self, harness: PressHarness) -> None:
        harness.press.record_page(PAGE_URL)
        harness.press.record_page(OTHER_URL)

        text = harness.export_markdown('brief')

        assert PAGE_URL not in text
        assert f'- Board: {OTHER_URL}' in list_section_lines(text, 'Pointers')

    def test_the_board_page_shows_the_link_once_it_is_recorded(self, harness: PressHarness) -> None:
        harness.press.record_page(PAGE_URL)

        harness.press.draw()
        page = harness.pages.files['board.html']

        (fact,) = [fact for fact in list_facts(page) if fact.label == 'Page']
        assert (fact.value, fact.link) == (PAGE_URL, PAGE_URL)
