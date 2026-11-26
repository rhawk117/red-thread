"""The command line for a ticket's plan: init writes plan.md, check reads it and changes nothing."""

import sys
from dataclasses import dataclass
from operator import attrgetter
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

from cyclopts import App, CycloptsError, Parameter
from red_thread_casefile.domain import STATE_DIRECTORY, build_case_id
from red_thread_casefile.errors import CaseFileError

from red_thread_plans.domain import PLAN_FILE, TICKET_HOME, Opening
from red_thread_plans.factory import Plans

if TYPE_CHECKING:
    from collections.abc import Sequence

PROGRAM = 'redthread-plan'
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2

type StrayTokens = Annotated[str, Parameter(show=False)]
type PlanOption = Annotated[
    Path, Parameter(help='the plan.md that init printed, or the directory that holds it')
]
type TitleOption = Annotated[str, Parameter(help='what the ticket delivers, as one line')]
type CaseOption = Annotated[
    tuple[str, ...], Parameter(help='a case under .red-thread/ the plan rests on; repeat it')
]
type RootOption = Annotated[str, Parameter(help='the repository root, by default this directory')]
type SlugOption = Annotated[
    str | None, Parameter(help='words for the plan id, by default taken from the title')
]


@Parameter(name='*')
@dataclass(slots=True, kw_only=True, frozen=True)
class InitArguments:
    title: TitleOption
    case: CaseOption = ()
    root: RootOption = '.'
    slug: SlugOption = None


@Parameter(name='*')
@dataclass(slots=True, kw_only=True, frozen=True)
class CheckArguments:
    plan: PlanOption


def locate_plan(path: Path) -> Path:
    return path.joinpath(PLAN_FILE) if path.is_dir() else path


@dataclass(slots=True, kw_only=True, frozen=True)
class InitCommand:
    plans: Plans
    name: str = 'init'
    summary: str = "write a ticket's plan.md with its frontmatter, beside the cases it rests on"

    def run(self, arguments: InitArguments) -> int:
        plan_id = build_case_id(self.plans.clock.now(), arguments.slug or arguments.title)
        root = Path(arguments.root)
        path = root.joinpath(STATE_DIRECTORY, TICKET_HOME, plan_id, PLAN_FILE)
        opening = Opening(id=plan_id, title=arguments.title, case_ids=arguments.case)
        created = self.plans.open_planner(path).open(opening)
        print(f'created {created}')
        return EXIT_OK


@dataclass(slots=True, kw_only=True, frozen=True)
class CheckCommand:
    plans: Plans
    name: str = 'check'
    summary: str = 'read a plan and report every fault; writes nothing'

    def run(self, arguments: CheckArguments) -> int:
        path = locate_plan(arguments.plan)
        checked = self.plans.open_planner(path).check()
        counts = f'{checked.criteria} criteria rest on {checked.entries} entries'
        print(f'checked {path.resolve()}: {counts}')
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
    commands = (
        InitCommand(plans=plans),
        CheckCommand(plans=plans),
    )
    app = App(
        name=PROGRAM,
        help="A ticket's plan in red-thread.",
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
