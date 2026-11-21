"""casefile page --url, driven through main(argv) against a temporary git repository."""

import json
from typing import TYPE_CHECKING

import pytest

from tests.casefile.lenses.reading import list_section_lines

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.commands.cli import CliHarness

URL = 'https://claude.ai/artifact/retry-queue'
OPEN = {'kind': 'open', 'text': 'who owns the queue', 'source': 'scout'}


def read_case_record(case: Path) -> dict[str, object]:
    record: dict[str, object] = json.loads(case.joinpath('case.json').read_text(encoding='utf-8'))
    return record


class TestPage:
    def test_the_link_is_stored_in_case_json_and_every_other_field_is_kept(
        self, cli: CliHarness, case: Path
    ) -> None:
        before = read_case_record(case)

        result = cli.page(case, URL)

        assert (result.code, result.err) == (0, '')
        assert result.out.strip() == f'recorded {URL}'
        assert read_case_record(case) == {**before, 'page_url': URL}

    def test_render_then_shows_the_page_line(self, cli: CliHarness, case: Path) -> None:
        cli.add(case, OPEN)
        cli.page(case, URL)

        result = cli.render(case)

        assert f'Page: {URL}' in result.out.splitlines()

    def test_export_pointers_then_show_the_board_link(self, cli: CliHarness, case: Path) -> None:
        cli.add(case, OPEN)
        cli.page(case, URL)

        cli.export(case, 'brief')

        brief = case.joinpath('out', 'brief.md').read_text(encoding='utf-8')
        assert f'- Board: {URL}' in list_section_lines(brief, 'Pointers')

    def test_the_ledger_is_untouched(self, cli: CliHarness, case: Path) -> None:
        cli.add(case, OPEN)
        before = case.joinpath('ledger.jsonl').read_bytes()

        cli.page(case, URL)

        assert case.joinpath('ledger.jsonl').read_bytes() == before

    def test_a_second_link_replaces_the_first(self, cli: CliHarness, case: Path) -> None:
        cli.page(case, URL)

        cli.page(case, 'https://example.invalid/b')

        assert read_case_record(case)['page_url'] == 'https://example.invalid/b'

    @pytest.mark.parametrize(
        'url',
        [
            pytest.param('http://example.invalid/board', id='http'),
            pytest.param('example.invalid/board', id='no-scheme'),
            pytest.param('https://example.invalid/a b', id='whitespace'),
            pytest.param('javascript:alert(1)', id='javascript'),
        ],
    )
    def test_a_link_that_is_not_https_is_refused_and_case_json_is_not_rewritten(
        self, cli: CliHarness, case: Path, url: str
    ) -> None:
        before = case.joinpath('case.json').read_bytes()

        result = cli.page(case, url)

        assert result.code == 1
        assert result.out == ''
        assert result.err.startswith('casefile: ')
        assert 'not an https link' in result.err
        assert case.joinpath('case.json').read_bytes() == before

    def test_a_directory_that_is_not_a_case_is_an_error(self, cli: CliHarness) -> None:
        result = cli.page(cli.git.root.joinpath('.red-thread', 'nothing-here'), URL)

        assert result.code == 1
        assert result.err.startswith('casefile: ')
