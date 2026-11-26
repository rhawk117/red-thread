"""The command line that skills and agents call to store a plan: revise."""

import sys
from dataclasses import dataclass
from operator import attrgetter
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

from cyclopts import App, CycloptsError, Parameter
from red_thread_casefile.cli import read_input
from red_thread_casefile.errors import CaseFileError

from red_thread_plans.errors import PlanShapeError
from red_thread_plans.factory import Plans
from red_thread_plans.schemas import decode_draft

if TYPE_CHECKING:
    from collections.abc import Sequence

PROGRAM = 'redthread-plan'
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2

type StrayTokens = Annotated[str, Parameter(show=False)]
type CaseOption = Annotated[Path, Parameter(help='the case directory that init printed')]
type PlanFileOption = Annotated[
    str | None, Parameter(help='read the plan from this file instead of standard input')
]


@Parameter(name='*')
@dataclass(slots=True, kw_only=True, frozen=True)
class ReviseArguments:
    case: CaseOption
    file: PlanFileOption = None


@dataclass(slots=True, kw_only=True, frozen=True)
class ReviseCommand:
    plans: Plans
    name: str = 'revise'
    summary: str = 'check a plan whole, then store it as the next revision'

    def run(self, arguments: ReviseArguments) -> int:
        draft = decode_draft(read_input(arguments.file))
        if isinstance(draft, PlanShapeError):
            raise draft

        stored = self.plans.open_planner(arguments.case).propose(draft)
        print(f'stored revision {stored.plan.revision} at {stored.path}')
        print(f'wrote {stored.page}')
        if stored.redactions:
            print(f'redacted {stored.redactions} secrets before storing')
        return EXIT_OK


@dataclass(slots=True, kw_only=True, frozen=True)
class CommandMenu:
    names: tuple[str, ...]

    def report_problem(self, *tokens: StrayTokens) -> int:
        problem = f'unknown command "{tokens[0]}"' if tokens else 'a command is required'
        print(f'{PROGRAM}: {problem}; choose from {", ".join(self.names)}', file=sys.stderr)
        return EXIT_USAGE


def create_app(plans: Plans | None = None) -> App:
    plans = plans or Plans()
    commands = (ReviseCommand(plans=plans),)
    app = App(
        name=PROGRAM,
        help='The red-thread plan.',
        version_flags=(),
        default_parameter=Parameter(negative=()),
        exit_on_error=False,
        print_error=False,
        result_action='return_value',
    )
    app.default(CommandMenu(names=tuple(map(attrgetter('name'), commands))).report_problem)
    for command in commands:
        app.command(command.run, name=command.name, help=command.summary)
    return app


def main(argv: Sequence[str] | None = None) -> int:
    try:
        code = create_app()(argv)
    except CycloptsError as error:
        print(f'{PROGRAM}: {error}', file=sys.stderr)
        return EXIT_USAGE
    except CaseFileError as error:
        print(f'{PROGRAM}: {error}', file=sys.stderr)
        return EXIT_FAILED
    return code if isinstance(code, int) else EXIT_OK
