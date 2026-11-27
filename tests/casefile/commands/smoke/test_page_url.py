"""A page_url written by hand into the frontmatter: render and export show it, check judges it."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.domain import CASE_FILE

from tests.casefile.ledger.builders import PAGE_URL
from tests.casefile.lenses.reading import list_section_lines

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.commands.cli import CliHarness

OPEN = {'kind': 'open', 'text': 'who owns the queue', 'source': 'scout'}
UNSET = 'page_url: null'


def write_page_url(case: Path, url: str) -> None:
    case_file = case.joinpath(CASE_FILE)
    text = case_file.read_text(encoding='utf-8')
    assert UNSET in text
    case_file.write_text(text.replace(UNSET, f"page_url: '{url}'"), encoding='utf-8')


def unfit_url_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        'url',
        [
            pytest.param('http://example.invalid/board', id='http'),
            pytest.param('example.invalid/board', id='no-scheme'),
            pytest.param('https://example.invalid/a b', id='whitespace'),
            pytest.param('javascript:alert(1)', id='javascript'),
        ],
    )


class TestPageUrl:
    @pytest.fixture
    def published(self, cli: CliHarness, case: Path) -> Path:
        cli.write(case, OPEN)
        write_page_url(case, PAGE_URL)
        return case

    def test_init_leaves_the_page_url_unset_for_the_skill_to_write(self, case: Path) -> None:
        assert UNSET in case.joinpath(CASE_FILE).read_text(encoding='utf-8')

    def test_render_shows_the_page_line(self, cli: CliHarness, published: Path) -> None:
        result = cli.render(published)

        assert f'Page: {PAGE_URL}' in result.out.splitlines()

    def test_export_pointers_show_the_board_link(self, cli: CliHarness, published: Path) -> None:
        cli.export(published, 'brief')

        brief = published.joinpath('out', 'brief.md').read_text(encoding='utf-8')
        assert f'- Board: {PAGE_URL}' in list_section_lines(brief, 'Pointers')

    def test_check_passes_an_https_link(self, cli: CliHarness, published: Path) -> None:
        result = cli.check(published)

        assert result.code == 0

    @unfit_url_cases()
    def test_a_link_that_is_not_https_is_a_check_fault(
        self, cli: CliHarness, case: Path, url: str
    ) -> None:
        write_page_url(case, url)

        result = cli.check(case)

        assert result.code == 1
        assert 'is not an https link' in result.out
