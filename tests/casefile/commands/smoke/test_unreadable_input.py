"""add --file and export --plan on a file that cannot be read."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.domain import PROGRAM

if TYPE_CHECKING:
    from pathlib import Path

    from _pytest.mark import ParameterSet

    from tests.casefile.commands.cli import CliHarness, CliRun


@dataclass(slots=True, kw_only=True, frozen=True)
class UnreadableFile:
    name: str
    command: str
    path_kind: str

    @property
    def param(self) -> ParameterSet:
        return pytest.param(self, id=self.name)


def unreadable_file_cases() -> pytest.MarkDecorator:
    scenarios = [
        UnreadableFile(name='add-missing-file', command='add', path_kind='missing'),
        UnreadableFile(name='add-directory-as-file', command='add', path_kind='directory'),
        UnreadableFile(name='export-missing-plan', command='export', path_kind='missing'),
        UnreadableFile(name='export-directory-as-plan', command='export', path_kind='directory'),
    ]
    return pytest.mark.parametrize('scenario', [scenario.param for scenario in scenarios])


class TestUnreadableInput:
    def locate(self, cli: CliHarness, scenario: UnreadableFile) -> Path:
        located = cli.git.root.parent.joinpath('input-under-test')
        if scenario.path_kind == 'directory':
            located.mkdir()
        return located

    def run_command(
        self, cli: CliHarness, case: Path, scenario: UnreadableFile, path: Path
    ) -> CliRun:
        if scenario.command == 'add':
            return cli.run('add', '--case', str(case), '--round', '1', '--file', str(path))

        return cli.run('export', '--case', str(case), '--lens', 'brief', '--plan', str(path))

    @unreadable_file_cases()
    def test_the_failure_is_reported_on_standard_error_with_exit_one(
        self, cli: CliHarness, case: Path, scenario: UnreadableFile
    ) -> None:
        path = self.locate(cli, scenario)

        result = self.run_command(cli, case, scenario, path)

        assert result.code == 1
        assert result.out == ''
        assert result.err.startswith(f'{PROGRAM}: ')
        assert 'cannot be read' in result.err
        assert str(path) in result.err

    @unreadable_file_cases()
    def test_nothing_is_stored_or_written(
        self, cli: CliHarness, case: Path, scenario: UnreadableFile
    ) -> None:
        path = self.locate(cli, scenario)

        self.run_command(cli, case, scenario, path)

        assert not case.joinpath('ledger.jsonl').exists()
        assert not case.joinpath('out').exists()
        assert 'Entries: 0 live, 0 retired' in cli.render(case).out
