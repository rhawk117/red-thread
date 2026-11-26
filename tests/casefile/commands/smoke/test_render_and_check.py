"""casefile render and check, driven through main(argv) against a temporary git repository."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.domain import PROGRAM

from tests.casefile.ledger.builders import KNOWN

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.commands.cli import CliHarness

URL_KNOWN = {**KNOWN, 'cite': 'https://example.invalid/docs#retries'}


def create_open_records(count: int) -> list[dict[str, object]]:
    return [
        {'kind': 'open', 'text': f'question {number}', 'source': 'scout'} for number in range(count)
    ]


class TestRender:
    def test_board_lists_the_live_entries_under_their_sections(
        self, cli: CliHarness, case: Path
    ) -> None:
        cli.add(case, KNOWN, *create_open_records(1))

        result = cli.render(case)

        assert (result.code, result.err) == (0, '')
        assert result.out.startswith(f'# {case.name}')
        assert '## Known (1)' in result.out
        assert '## Open (1)' in result.out
        assert '[e1]' in result.out

    def test_board_is_capped_and_full_shows_every_entry(self, cli: CliHarness, case: Path) -> None:
        cli.add(case, *create_open_records(9))

        capped = cli.render(case)
        full = cli.render(case, '--full')

        assert '(+3 earlier, shown by render --full)' in capped.out
        assert 'question 0' not in capped.out
        assert 'earlier' not in full.out
        assert 'question 0' in full.out

    def test_entry_recorded_at_an_earlier_commit_is_marked_as_a_lead(
        self, cli: CliHarness, case: Path
    ) -> None:
        recorded_at = cli.git.head
        cli.add(case, *create_open_records(1))
        cli.git.write('src/other.py', 'x = 1\n')
        cli.git.commit('move on')

        result = cli.render(case)

        assert f'lead, recorded at {recorded_at[:7]}' in result.out

    def test_retired_entry_is_gone_from_the_board(self, cli: CliHarness, case: Path) -> None:
        cli.add(case, *create_open_records(1))
        cli.add(
            case, {'kind': 'open', 'text': 'replacement', 'source': 'scout', 'supersedes': ['e1']}
        )

        result = cli.render(case)

        assert 'question 0' not in result.out
        assert 'replacement' in result.out
        assert 'Entries: 1 live, 1 retired' in result.out

    def test_corrupt_ledger_line_is_reported_with_its_file_and_line_number(
        self, cli: CliHarness, case: Path
    ) -> None:
        cli.add(case, *create_open_records(1))
        ledger = case.joinpath('ledger.jsonl')
        ledger.write_text(ledger.read_text(encoding='utf-8') + 'broken line\n', encoding='utf-8')

        result = cli.render(case)

        assert result.code == 1
        assert result.out == ''
        assert result.err.startswith(f'{PROGRAM}: ')
        assert f'{ledger.resolve()} line 2' in result.err

    def test_directory_that_is_not_a_case_is_an_error(self, cli: CliHarness) -> None:
        result = cli.render(cli.git.root.joinpath('.red-thread', 'nothing-here'))

        assert result.code == 1
        assert result.err.startswith(f'{PROGRAM}: ')


class TestCheck:
    @pytest.fixture
    def cited(self, cli: CliHarness, case: Path) -> Path:
        cli.add(case, KNOWN)
        return case

    def test_citation_that_still_holds_exits_zero(self, cli: CliHarness, cited: Path) -> None:
        result = cli.check(cited)

        assert result.code == 0
        assert result.out.splitlines()[0] == (
            'checked 1 citations: 1 ok, 0 moved, 0 changed, 0 missing, 0 unchecked'
        )

    def test_moved_citation_exits_zero_and_names_the_new_line(
        self, cli: CliHarness, cited: Path
    ) -> None:
        queue = cli.git.root.joinpath('src', 'queue.py')
        queue.write_text('# header\n' + queue.read_text(encoding='utf-8'), encoding='utf-8')

        result = cli.check(cited)

        assert result.code == 0
        assert '1 moved' in result.out
        assert 'now at line 4' in result.out

    def test_changed_citation_exits_one_and_is_listed(self, cli: CliHarness, cited: Path) -> None:
        queue = cli.git.root.joinpath('src', 'queue.py')
        queue.write_text('import time\ndef retry(job):\n    pass\n', encoding='utf-8')

        result = cli.check(cited)

        assert result.code == 1
        assert '1 changed' in result.out
        assert '- [e1] changed: `src/queue.py:3`' in result.out
        assert 'no longer evidence' in result.out

    def test_missing_citation_exits_one_and_is_listed(self, cli: CliHarness, cited: Path) -> None:
        cli.git.root.joinpath('src', 'queue.py').unlink()

        result = cli.check(cited)

        assert result.code == 1
        assert '1 missing' in result.out
        assert '- [e1] missing:' in result.out

    def test_url_citation_is_unchecked_and_exits_zero(self, cli: CliHarness, case: Path) -> None:
        cli.add(case, URL_KNOWN)

        result = cli.check(case)

        assert result.code == 0
        assert '1 unchecked' in result.out

    def test_one_failing_citation_among_good_ones_exits_one(
        self, cli: CliHarness, case: Path
    ) -> None:
        cli.add(case, KNOWN, URL_KNOWN, {**KNOWN, 'cite': 'src/queue.py:1'})
        queue = cli.git.root.joinpath('src', 'queue.py')
        queue.write_text('changed\ndef retry(job):\n    time.sleep(job.delay)\n', encoding='utf-8')

        result = cli.check(case)

        assert result.code == 1
        assert '1 changed' in result.out
        assert '1 ok' in result.out

    def test_retired_citation_is_not_checked(self, cli: CliHarness, cited: Path) -> None:
        cli.add(cited, {'kind': 'open', 'text': 'gone', 'source': 'scout', 'supersedes': ['e1']})
        cli.git.root.joinpath('src', 'queue.py').unlink()

        result = cli.check(cited)

        assert result.code == 0
        assert result.out.startswith('checked 0 citations')

    def test_corrupt_ledger_line_stops_the_check_with_its_file_and_line_number(
        self, cli: CliHarness, cited: Path
    ) -> None:
        ledger = cited.joinpath('ledger.jsonl')
        ledger.write_text('{broken\n' + ledger.read_text(encoding='utf-8'), encoding='utf-8')

        result = cli.check(cited)

        assert result.code == 1
        assert result.err.startswith(f'{PROGRAM}: ')
        assert f'{ledger.resolve()} line 1' in result.err
