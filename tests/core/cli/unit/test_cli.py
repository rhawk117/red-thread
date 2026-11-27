from dataclasses import dataclass

import pytest
from cyclopts import Parameter
from red_thread_core.cli import (
    EXIT_FAILED,
    EXIT_OK,
    EXIT_USAGE,
    CommandMenu,
    create_app,
    join_choices,
    run_app,
)
from red_thread_core.errors import RedThreadError

from tests.params import as_params

PROGRAM = 'probe-tool'
CHOICES = ('init', 'render', 'check')


@Parameter(name='*')
@dataclass(slots=True, kw_only=True, frozen=True)
class ProbeArguments:
    label: str


@dataclass(slots=True, kw_only=True, frozen=True)
class ProbeCommand:
    name: str = 'probe'
    summary: str = 'a command for the tests'
    code: int = EXIT_OK
    failure: RedThreadError | None = None

    def run(self, _arguments: ProbeArguments) -> int:
        if self.failure is not None:
            raise self.failure
        return self.code


@dataclass(slots=True, kw_only=True, frozen=True)
class ExitScenario:
    name: str
    command: ProbeCommand
    argv: tuple[str, ...]
    code: int
    marks: tuple[pytest.MarkDecorator, ...] = ()


def join_choices_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        ('names', 'expected'),
        [
            pytest.param(('check',), 'check', id='one'),
            pytest.param(('init', 'check'), 'init or check', id='two'),
            pytest.param(('init', 'render', 'check'), 'init, render or check', id='three'),
        ],
    )


def run_app_exit_cases() -> pytest.MarkDecorator:
    scenarios = (
        ExitScenario(
            name='success', command=ProbeCommand(), argv=('probe', '--label', 'x'), code=EXIT_OK
        ),
        ExitScenario(
            name='int-result', command=ProbeCommand(code=3), argv=('probe', '--label', 'x'), code=3
        ),
        ExitScenario(
            name='red-thread-error',
            command=ProbeCommand(failure=RedThreadError('the case is corrupt')),
            argv=('probe', '--label', 'x'),
            code=EXIT_FAILED,
        ),
        ExitScenario(
            name='unknown-option',
            command=ProbeCommand(),
            argv=('probe', '--label', 'x', '--bogus'),
            code=EXIT_USAGE,
        ),
    )
    return pytest.mark.parametrize('scenario', as_params(scenarios))


class TestJoinChoices:
    @join_choices_cases()
    def test_names_read_as_a_list_ending_in_or(self, names: tuple[str, ...], expected: str) -> None:
        assert join_choices(names) == expected


class TestCommandMenu:
    menu = CommandMenu(program=PROGRAM, names=CHOICES)

    def test_missing_command_names_the_choices(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = self.menu.report_problem()
        assert (code, capsys.readouterr().err) == (
            EXIT_USAGE,
            'probe-tool: a command is required; choose from init, render or check\n',
        )

    def test_unknown_command_names_the_token(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = self.menu.report_problem('bogus', 'extra')
        assert (code, capsys.readouterr().err) == (
            EXIT_USAGE,
            'probe-tool: unknown command "bogus"; choose from init, render or check\n',
        )


class TestRunApp:
    @run_app_exit_cases()
    def test_exit_code_follows_the_outcome(self, scenario: ExitScenario) -> None:
        app = create_app(PROGRAM, 'A probe for the tests.', (scenario.command,))
        assert run_app(PROGRAM, app, scenario.argv) == scenario.code

    def test_red_thread_error_is_printed_under_the_program(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        command = ProbeCommand(failure=RedThreadError('the case is corrupt'))
        app = create_app(PROGRAM, 'A probe for the tests.', (command,))
        code = run_app(PROGRAM, app, ('probe', '--label', 'x'))
        assert (code, capsys.readouterr().err) == (
            EXIT_FAILED,
            'probe-tool: the case is corrupt\n',
        )

    def test_usage_error_is_printed_under_the_program(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        app = create_app(PROGRAM, 'A probe for the tests.', (ProbeCommand(),))
        code = run_app(PROGRAM, app, ('probe', '--label', 'x', '--bogus'))
        assert code == EXIT_USAGE
        assert capsys.readouterr().err.startswith('probe-tool: ')
