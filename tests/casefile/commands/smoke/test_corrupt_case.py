"""Every command over a case.md it cannot read reports the fault and changes nothing."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.domain import CASE_FILE, PROGRAM

from tests.casefile.ledger.cases import corrupt_case_params
from tests.casefile.ledger.markdown import append_text
from tests.params import as_params

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.commands.cli import CliHarness, CliRun

OPEN = {'kind': 'open', 'text': 'who owns the queue', 'source': 'scout'}
BROKEN_LINE = 'this is not an entry'


@dataclass(slots=True, kw_only=True, frozen=True)
class CommandCall:
    name: str
    argv: tuple[str, ...]
    marks: tuple[pytest.MarkDecorator, ...] = ()


def create_calls() -> list[CommandCall]:
    return [
        CommandCall(name='render', argv=('render',)),
        CommandCall(name='export', argv=('export', '--lens', 'brief')),
    ]


def loading_command_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('call', as_params(create_calls()))


def corrupt_case_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('text', corrupt_case_params())


def run_call(cli: CliHarness, case: Path, call: CommandCall) -> CliRun:
    return cli.run(*call.argv, '--case', str(case), stdin='')


def assert_nothing_written(case: Path) -> None:
    assert not case.joinpath('out').exists()
    assert not case.joinpath('board.html').exists()


class TestCorruptCaseFile:
    @loading_command_cases()
    @corrupt_case_cases()
    def test_the_command_names_case_md_and_exits_one_without_a_traceback(
        self, cli: CliHarness, case: Path, call: CommandCall, text: str
    ) -> None:
        case.joinpath(CASE_FILE).write_text(text, encoding='utf-8')

        result = run_call(cli, case, call)

        assert result.code == 1
        assert result.out == ''
        assert result.err.startswith(f'{PROGRAM}: the case file cannot be read')
        assert f'- {CASE_FILE}' in result.err
        assert 'Traceback' not in result.err

    @corrupt_case_cases()
    def test_check_names_case_md_as_a_fault_and_exits_one(
        self, cli: CliHarness, case: Path, text: str
    ) -> None:
        case.joinpath(CASE_FILE).write_text(text, encoding='utf-8')

        result = cli.check(case)

        assert (result.code, result.err) == (1, '')
        assert f'- {CASE_FILE}' in result.out

    @loading_command_cases()
    @corrupt_case_cases()
    def test_nothing_is_changed_or_written(
        self, cli: CliHarness, case: Path, call: CommandCall, text: str
    ) -> None:
        case_file = case.joinpath(CASE_FILE)
        case_file.write_text(text, encoding='utf-8')

        run_call(cli, case, call)

        assert case_file.read_text(encoding='utf-8') == text
        assert_nothing_written(case)


class TestStrayLine:
    @pytest.fixture
    def broken(self, cli: CliHarness, case: Path) -> Path:
        cli.write(case, OPEN)
        append_text(case, f'{BROKEN_LINE}\n', 'T1')
        return case

    @loading_command_cases()
    def test_the_command_names_the_file_and_line_and_exits_one_without_a_traceback(
        self, cli: CliHarness, broken: Path, call: CommandCall
    ) -> None:
        result = run_call(cli, broken, call)

        assert result.code == 1
        assert result.out == ''
        assert '- threads/T1.md:1: this text is outside' in result.err
        assert 'Traceback' not in result.err

    @loading_command_cases()
    def test_the_broken_file_is_left_as_it_was(
        self, cli: CliHarness, broken: Path, call: CommandCall
    ) -> None:
        run_call(cli, broken, call)

        thread = broken.joinpath('threads', 'T1.md')
        assert thread.read_text(encoding='utf-8') == f'{BROKEN_LINE}\n'
        assert_nothing_written(broken)
