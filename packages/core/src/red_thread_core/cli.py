"""Shared command-line scaffolding: exit codes, the command menu and the app runner."""

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Never, Protocol, runtime_checkable

from cyclopts import App, CycloptsError, Parameter

from red_thread_core.errors import RedThreadError

if TYPE_CHECKING:
    from collections.abc import Sequence

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2

type StrayTokens = Annotated[str, Parameter(show=False)]


@runtime_checkable
class Command(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def summary(self) -> str: ...

    def run(self, arguments: Never, /) -> int: ...


def join_choices(names: Sequence[str]) -> str:
    *rest, last = names
    if not rest:
        return last
    return f'{", ".join(rest)} or {last}'


@dataclass(slots=True, kw_only=True, frozen=True)
class CommandMenu:
    program: str
    names: tuple[str, ...]

    def report_problem(self, *tokens: StrayTokens) -> int:
        problem = f'unknown command "{tokens[0]}"' if tokens else 'a command is required'
        print(f'{self.program}: {problem}; choose from {join_choices(self.names)}', file=sys.stderr)
        return EXIT_USAGE


def create_app(program: str, help_text: str, commands: Sequence[Command]) -> App:
    app = App(
        name=program,
        help=help_text,
        version_flags=(),
        default_parameter=Parameter(negative=()),
        exit_on_error=False,
        print_error=False,
        result_action='return_value',
    )
    names = tuple(command.name for command in commands)
    app.default(CommandMenu(program=program, names=names).report_problem)
    for command in commands:
        app.command(command.run, name=command.name, help=command.summary)
    return app


def run_app(program: str, app: App, argv: Sequence[str] | None) -> int:
    try:
        code = app(argv)
    except CycloptsError as error:
        print(f'{program}: {error}', file=sys.stderr)
        return EXIT_USAGE
    except RedThreadError as error:
        print(f'{program}: {error}', file=sys.stderr)
        return EXIT_FAILED
    return code if isinstance(code, int) else EXIT_OK
