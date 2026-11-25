"""casefile add, driven through main(argv) against a temporary git repository."""

import json
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.domain import PROGRAM

from tests.casefile.batches.cases import invalid_thread_params

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.commands.cli import CliHarness

OPEN = {'kind': 'open', 'text': 'what stalls the queue', 'source': 'scout'}
KNOWN = {
    'kind': 'known',
    'text': 'the sleep blocks the queue',
    'source': 'scout',
    'cite': 'src/queue.py:3',
}
LEAKED = 'AKIAIOSFODNN7EXAMPLE'


def invalid_thread_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('thread', invalid_thread_params())


class TestAdd:
    def test_batch_from_a_file_is_stored_and_its_refs_are_printed(
        self, cli: CliHarness, case: Path
    ) -> None:
        result = cli.add(case, OPEN, KNOWN)

        assert (result.code, result.out, result.err) == (0, 'stored e1 e2\n', '')
        assert len(case.joinpath('ledger.jsonl').read_text(encoding='utf-8').splitlines()) == 2

    def test_batch_from_standard_input_is_stored(self, cli: CliHarness, case: Path) -> None:
        result = cli.run(
            'add', '--case', str(case), '--round', '1', stdin=json.dumps([OPEN, KNOWN])
        )

        assert (result.code, result.out, result.err) == (0, 'stored e1 e2\n', '')

    def test_single_object_on_standard_input_is_a_batch_of_one(
        self, cli: CliHarness, case: Path
    ) -> None:
        result = cli.run('add', '--case', str(case), '--round', '1', stdin=json.dumps(OPEN))

        assert (result.code, result.out) == (0, 'stored e1\n')

    def test_thread_entries_are_stored_under_the_thread(self, cli: CliHarness, case: Path) -> None:
        cli.add(case, OPEN)

        result = cli.add(case, OPEN, thread='T1')

        assert (result.code, result.out) == (0, 'stored T1.e1\n')
        assert case.joinpath('threads', 'T1.jsonl').is_file()


class TestAddValidation:
    @invalid_thread_cases()
    def test_invalid_thread_name_is_refused_and_nothing_is_stored(
        self, cli: CliHarness, case: Path, thread: str
    ) -> None:
        result = cli.add(case, OPEN, thread=thread)

        assert result.code == 1
        assert result.out == ''
        assert result.err.startswith(f'{PROGRAM}: ')
        assert 'is not a thread name' in result.err
        assert not case.joinpath('ledger.jsonl').exists()
        assert list(case.joinpath('threads').iterdir()) == []

    def test_bad_batch_is_refused_whole_and_every_problem_is_listed(
        self, cli: CliHarness, case: Path
    ) -> None:
        uncited = {**KNOWN, 'cite': None}
        shape = {**OPEN, 'kind': 'finding'}
        decision = {'kind': 'decision', 'text': 'use a queue', 'source': 'scout'}

        result = cli.add(case, OPEN, uncited, shape, decision)

        assert result.code == 1
        assert result.out == ''
        assert result.err.startswith(f'{PROGRAM}: nothing was stored')
        assert all(f'entry {position}:' in result.err for position in (2, 3, 4))
        assert 'entry 1:' not in result.err
        assert not case.joinpath('ledger.jsonl').exists()

    def test_unusable_batch_text_is_an_error_not_a_traceback(
        self, cli: CliHarness, case: Path
    ) -> None:
        result = cli.run('add', '--case', str(case), '--round', '1', stdin='not json at all')

        assert result.code == 1
        assert result.out == ''
        assert result.err.startswith(f'{PROGRAM}: the batch is not usable')

    def test_batch_file_that_does_not_exist_is_an_error_with_the_casefile_prefix(
        self, cli: CliHarness, case: Path
    ) -> None:
        result = cli.run(
            'add', '--case', str(case), '--round', '1', '--file', str(case.joinpath('nope.json'))
        )

        assert result.code == 1
        assert result.err.startswith(f'{PROGRAM}: ')

    def test_secret_is_redacted_before_it_is_stored_and_the_count_is_printed(
        self, cli: CliHarness, case: Path
    ) -> None:
        leaking = {**OPEN, 'text': f'the key {LEAKED} is in the log'}

        result = cli.add(case, leaking)

        assert result.code == 0
        assert result.out == 'stored e1\nredacted 1 secrets before storing\n'
        stored = case.joinpath('ledger.jsonl').read_text(encoding='utf-8')
        assert LEAKED not in stored
        assert '[REDACTED:aws-key]' in stored

    def test_quote_is_captured_from_the_cited_line(self, cli: CliHarness, case: Path) -> None:
        cli.add(case, KNOWN)

        [line] = case.joinpath('ledger.jsonl').read_text(encoding='utf-8').splitlines()
        assert json.loads(line)['quote'] == 'time.sleep(job.delay)'

    def test_quote_found_on_another_line_is_refused_with_that_line(
        self, cli: CliHarness, case: Path
    ) -> None:
        misquoted = {**KNOWN, 'cite': 'src/queue.py:1', 'quote': 'return job.run()'}

        result = cli.add(case, misquoted)

        assert result.code == 1
        assert 'The quoted text is at line 4' in result.err

    def test_cite_of_a_missing_line_is_refused(self, cli: CliHarness, case: Path) -> None:
        result = cli.add(case, {**KNOWN, 'cite': 'src/queue.py:99'})

        assert result.code == 1
        assert 'src/queue.py:99 does not resolve' in result.err

    def test_adding_to_a_directory_that_is_not_a_case_is_an_error(self, cli: CliHarness) -> None:
        elsewhere = cli.git.root.joinpath('.red-thread', 'nothing-here')

        result = cli.add(elsewhere, OPEN)

        assert result.code == 1
        assert result.err.startswith(f'{PROGRAM}: ')
        assert 'no case.json' in result.err
