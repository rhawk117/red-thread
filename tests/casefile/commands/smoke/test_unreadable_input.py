"""export --selection on a file that cannot be read."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.domain import PROGRAM

from tests.params import as_params

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.commands.cli import CliHarness, CliRun


@dataclass(slots=True, kw_only=True, frozen=True)
class UnreadableFile:
    name: str
    command: str
    path_kind: str
    marks: tuple[pytest.MarkDecorator, ...] = ()


def unreadable_file_cases() -> pytest.MarkDecorator:
    scenarios = [
        UnreadableFile(name='export-missing-selection', command='export', path_kind='missing'),
        UnreadableFile(
            name='export-directory-as-selection', command='export', path_kind='directory'
        ),
    ]
    return pytest.mark.parametrize('scenario', as_params(scenarios))


class TestUnreadableInput:
    def locate(self, cli: CliHarness, scenario: UnreadableFile) -> Path:
        located = cli.git.root.parent.joinpath('input-under-test')
        if scenario.path_kind == 'directory':
            located.mkdir()
        return located

    def run_command(self, cli: CliHarness, case: Path, path: Path) -> CliRun:
        return cli.run('export', '--case', str(case), '--lens', 'brief', '--selection', str(path))

    @unreadable_file_cases()
    def test_the_failure_is_reported_on_standard_error_with_exit_one(
        self, cli: CliHarness, case: Path, scenario: UnreadableFile
    ) -> None:
        path = self.locate(cli, scenario)

        result = self.run_command(cli, case, path)

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

        self.run_command(cli, case, path)

        assert not case.joinpath('out').exists()
        assert 'Entries: 0 live, 0 retired' in cli.render(case).out
