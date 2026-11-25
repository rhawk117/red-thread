"""Every command that reads a corrupt case.json or ledger line reports it and changes nothing."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.domain import PROGRAM

from tests.casefile.ledger.cases import corrupt_case_params

if TYPE_CHECKING:
    from pathlib import Path

    from _pytest.mark import ParameterSet

    from tests.casefile.commands.cli import CliHarness, CliRun

URL = 'https://claude.ai/artifact/retry-queue'
BATCH = '[{"kind": "open", "text": "who owns the queue", "source": "scout"}]'
BROKEN_LINE = 'this is not a ledger entry'


@dataclass(slots=True, kw_only=True, frozen=True)
class CommandCall:
    name: str
    argv: tuple[str, ...]
    stdin: str
    reads_case: bool
    reads_ledger: bool

    @property
    def param(self) -> ParameterSet:
        return pytest.param(self, id=self.name)


def create_calls() -> list[CommandCall]:
    return [
        CommandCall(name='render', argv=('render',), stdin='', reads_case=True, reads_ledger=True),
        CommandCall(name='check', argv=('check',), stdin='', reads_case=False, reads_ledger=True),
        CommandCall(
            name='export',
            argv=('export', '--lens', 'brief'),
            stdin='',
            reads_case=True,
            reads_ledger=True,
        ),
        CommandCall(
            name='add',
            argv=('add', '--round', '1'),
            stdin=BATCH,
            reads_case=False,
            reads_ledger=True,
        ),
        CommandCall(
            name='page', argv=('page', '--url', URL), stdin='', reads_case=True, reads_ledger=False
        ),
    ]


def case_command_cases() -> pytest.MarkDecorator:
    calls = [call for call in create_calls() if call.reads_case]
    return pytest.mark.parametrize('call', [call.param for call in calls])


def ledger_command_cases() -> pytest.MarkDecorator:
    calls = [call for call in create_calls() if call.reads_ledger]
    return pytest.mark.parametrize('call', [call.param for call in calls])


def corrupt_case_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('text', corrupt_case_params())


class TestCorruptCaseFile:
    def run_call(self, cli: CliHarness, case: Path, call: CommandCall) -> CliRun:
        return cli.run(*call.argv, '--case', str(case), stdin=call.stdin)

    @case_command_cases()
    @corrupt_case_cases()
    def test_the_command_names_the_file_and_exits_one_without_a_traceback(
        self, cli: CliHarness, case: Path, call: CommandCall, text: str
    ) -> None:
        case_file = case.joinpath('case.json')
        case_file.write_text(text, encoding='utf-8')

        result = self.run_call(cli, case, call)

        assert result.code == 1
        assert result.out == ''
        assert result.err.startswith(f'{PROGRAM}: {case_file} is not a case record (')
        assert 'Traceback' not in result.err
        assert result.err.count('\n') == 1

    @case_command_cases()
    @corrupt_case_cases()
    def test_nothing_is_changed_or_written(
        self, cli: CliHarness, case: Path, call: CommandCall, text: str
    ) -> None:
        case_file = case.joinpath('case.json')
        case_file.write_text(text, encoding='utf-8')
        ledger_before = case.joinpath('ledger.jsonl').exists()

        self.run_call(cli, case, call)

        assert case_file.read_text(encoding='utf-8') == text
        assert case.joinpath('ledger.jsonl').exists() == ledger_before
        assert not case.joinpath('out').exists()
        assert not case.joinpath('board.html').exists()


class TestCorruptLedgerLine:
    @ledger_command_cases()
    def test_the_command_names_the_file_and_line_and_exits_one_without_a_traceback(
        self, cli: CliHarness, case: Path, call: CommandCall
    ) -> None:
        ledger = case.joinpath('ledger.jsonl')
        ledger.write_text(f'{BROKEN_LINE}\n', encoding='utf-8')

        result = cli.run(*call.argv, '--case', str(case), stdin=call.stdin)

        assert result.code == 1
        assert result.out == ''
        assert result.err.startswith(f'{PROGRAM}: {ledger} line 1 is not a ledger entry')
        assert 'Traceback' not in result.err

    @ledger_command_cases()
    def test_the_broken_ledger_is_left_as_it_was(
        self, cli: CliHarness, case: Path, call: CommandCall
    ) -> None:
        ledger = case.joinpath('ledger.jsonl')
        ledger.write_text(f'{BROKEN_LINE}\n', encoding='utf-8')

        cli.run(*call.argv, '--case', str(case), stdin=call.stdin)

        assert ledger.read_text(encoding='utf-8') == f'{BROKEN_LINE}\n'
        assert not case.joinpath('out').exists()
