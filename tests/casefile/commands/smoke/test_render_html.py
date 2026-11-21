"""casefile render --html, driven through main(argv) against a temporary git repository."""

from typing import TYPE_CHECKING

from tests.casefile.pages.html_reading import list_item_refs, list_spans
from tests.casefile.pages.promises import assert_page_holds_only_its_own_markup

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.commands.cli import CliHarness

SCRIPT = '<script>alert(1)</script>'


def create_open_records(count: int) -> list[dict[str, object]]:
    return [
        {'kind': 'open', 'text': f'question {number}', 'source': 'scout'} for number in range(count)
    ]


class TestRenderHtml:
    def test_board_html_is_written_in_the_case_and_named_after_the_text_board(
        self, cli: CliHarness, case: Path
    ) -> None:
        cli.add(case, *create_open_records(2))

        result = cli.render(case, '--html')

        assert (result.code, result.err) == (0, '')
        assert result.out.splitlines()[-1] == f'wrote {case.joinpath("board.html")}'
        assert case.joinpath('board.html').is_file()

    def test_the_text_board_is_unchanged_and_the_wrote_line_comes_after_it(
        self, cli: CliHarness, case: Path
    ) -> None:
        cli.add(case, *create_open_records(9))
        plain = cli.render(case)

        with_page = cli.render(case, '--html')

        assert with_page.out.splitlines()[:-1] == plain.out.splitlines()
        assert with_page.out.splitlines()[-1].startswith('wrote ')

    def test_the_page_shows_every_live_entry_though_the_text_board_is_capped(
        self, cli: CliHarness, case: Path
    ) -> None:
        cli.add(case, *create_open_records(9))

        result = cli.render(case, '--html')

        assert '(+3 earlier, shown by render --full)' in result.out
        page = case.joinpath('board.html').read_text(encoding='utf-8')
        assert list_item_refs(page) == [f'e{number}' for number in range(1, 10)]

    def test_without_html_no_page_is_written(self, cli: CliHarness, case: Path) -> None:
        cli.add(case, *create_open_records(1))

        cli.render(case)

        assert not case.joinpath('board.html').exists()

    def test_the_page_holds_no_raw_script_from_a_stored_entry(
        self, cli: CliHarness, case: Path
    ) -> None:
        cli.add(
            case,
            {
                'kind': 'open',
                'text': SCRIPT,
                'source': 'scout',
                'rests_on': SCRIPT,
                'verdict': 'INFERRED',
            },
        )

        cli.render(case, '--html')

        page = case.joinpath('board.html').read_text(encoding='utf-8')
        assert_page_holds_only_its_own_markup(page)
        assert page.lower().count('<script') == 3

    def test_the_page_flags_an_entry_whose_citation_changed(
        self, cli: CliHarness, case: Path
    ) -> None:
        cli.add(
            case,
            {'kind': 'known', 'text': 'the sleep', 'source': 'scout', 'cite': 'src/queue.py:3'},
        )
        queue = cli.git.root.joinpath('src', 'queue.py')
        queue.write_text('import time\ndef retry(job):\n    pass\n', encoding='utf-8')

        cli.render(case, '--html')

        page = case.joinpath('board.html').read_text(encoding='utf-8')
        assert [span.body for span in list_spans(page, 'state')] == ['changed']

    def test_a_directory_that_is_not_a_case_writes_no_page(self, cli: CliHarness) -> None:
        nowhere = cli.git.root.joinpath('.red-thread', 'nothing-here')

        result = cli.render(nowhere, '--html')

        assert result.code == 1
        assert not nowhere.joinpath('board.html').exists()
