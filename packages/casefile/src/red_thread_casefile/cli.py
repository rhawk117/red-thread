"""The command line that skills and agents call: init, add, render, check, export and page."""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

from cyclopts import App, CycloptsError, Parameter

from red_thread_casefile.domain import CaseKind, build_case_id
from red_thread_casefile.errors import CaseFileError, MalformedPlanError, UnreadableInputError
from red_thread_casefile.factory import CaseFiles
from red_thread_casefile.lenses import LensName
from red_thread_casefile.schemas import load_plan, parse_batch
from red_thread_casefile.services import Batch, ExportRequest, Framing
from red_thread_casefile.views import BoardOptions, CheckReport

if TYPE_CHECKING:
    from collections.abc import Sequence

PROGRAM = 'casefile'
COMMAND_NAMES = 'init, add, render, check, export or page'
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2

type StrayTokens = Annotated[str, Parameter(show=False)]
type CaseOption = Annotated[Path, Parameter(help='the case directory that init printed')]
type RootOption = Annotated[str, Parameter(help='the repository root, by default this directory')]
type TargetOption = Annotated[str, Parameter(help='the question, as one line')]
type KindOption = Annotated[CaseKind, Parameter(help='the kind of case')]
type BarOption = Annotated[str, Parameter(help='what the answer must establish')]
type SlugOption = Annotated[
    str | None, Parameter(help='words for the case id, by default taken from the target')
]
type PublishFlag = Annotated[bool, Parameter(help='the owner chose a published page')]
type RoundOption = Annotated[int, Parameter(name='--round', help='0 for framing, then the round')]
type ThreadOption = Annotated[str | None, Parameter(help='the thread a lead writes to, such as T1')]
type BatchFileOption = Annotated[
    str | None, Parameter(help='read the batch from this file instead of standard input')
]
type FullFlag = Annotated[bool, Parameter(help='show every live entry')]
type BoardFlag = Annotated[bool, Parameter(help='also write board.html in the case')]
type LensOption = Annotated[LensName, Parameter(help='the output to write')]
type PlanOption = Annotated[
    str | None, Parameter(help='read the plan from this file instead of standard input')
]
type PageFlag = Annotated[bool, Parameter(help='also write the output as a page')]
type UrlOption = Annotated[str, Parameter(help='the https link that publishing returned')]


@Parameter(name='*')
@dataclass(slots=True, kw_only=True, frozen=True)
class InitArguments:
    target: TargetOption
    kind: KindOption
    bar: BarOption
    root: RootOption = '.'
    slug: SlugOption = None
    publish: PublishFlag = False


@Parameter(name='*')
@dataclass(slots=True, kw_only=True, frozen=True)
class CaseArguments:
    case: CaseOption


@Parameter(name='*')
@dataclass(slots=True, kw_only=True, frozen=True)
class AddArguments:
    case: CaseOption
    round_number: RoundOption
    thread: ThreadOption = None
    file: BatchFileOption = None


@Parameter(name='*')
@dataclass(slots=True, kw_only=True, frozen=True)
class RenderArguments:
    case: CaseOption
    full: FullFlag = False
    html: BoardFlag = False


@Parameter(name='*')
@dataclass(slots=True, kw_only=True, frozen=True)
class ExportArguments:
    case: CaseOption
    lens: LensOption
    plan: PlanOption = None
    html: PageFlag = False


@Parameter(name='*')
@dataclass(slots=True, kw_only=True, frozen=True)
class PageArguments:
    case: CaseOption
    url: UrlOption


def read_input(path: str | None) -> str:
    if path is None:
        return str(sys.stdin.read())
    try:
        return Path(path).read_text(encoding='utf-8')
    except OSError as error:
        reason = error.strerror or 'the system gave no reason'
        raise UnreadableInputError(path=path, reason=reason) from error


@dataclass(slots=True, kw_only=True, frozen=True)
class InitCommand:
    cases: CaseFiles

    def run(self, arguments: InitArguments) -> int:
        case_id = build_case_id(self.cases.clock.now(), arguments.slug or arguments.target)
        directory = Path(arguments.root).joinpath('.red-thread', case_id)
        framing = Framing(
            id=case_id,
            target=arguments.target,
            kind=arguments.kind,
            bar=arguments.bar,
            publish=arguments.publish,
        )
        case = self.cases.bind(directory).frame(framing)
        languages = ', '.join(case.capabilities.languages) or 'none detected'
        print(f'created {directory.resolve()}')
        print(f'languages: {languages}')
        return 0


@dataclass(slots=True, kw_only=True, frozen=True)
class AddCommand:
    cases: CaseFiles

    def run(self, arguments: AddArguments) -> int:
        parsed = parse_batch(read_input(arguments.file))
        batch = Batch(
            drafts=parsed.drafts,
            problems=parsed.problems,
            round=arguments.round_number,
            thread=arguments.thread,
        )
        added = self.cases.bind(arguments.case).add(batch)
        refs = ' '.join(entry.ref for entry in added.entries)
        print(f'stored {refs}')
        if added.redactions:
            print(f'redacted {added.redactions} secrets before storing')
        return 0


@dataclass(slots=True, kw_only=True, frozen=True)
class RenderCommand:
    cases: CaseFiles

    def run(self, arguments: RenderArguments) -> int:
        directory = arguments.case
        options = BoardOptions.full() if arguments.full else BoardOptions()
        print(self.cases.bind(directory).show(options))
        if arguments.html:
            print(f'wrote {self.cases.open_press(directory).draw()}')
        return 0


@dataclass(slots=True, kw_only=True, frozen=True)
class CheckCommand:
    cases: CaseFiles

    def run(self, arguments: CaseArguments) -> int:
        report = CheckReport(findings=self.cases.bind(arguments.case).check())
        print(report.render())
        return int(report.has_failures)


@dataclass(slots=True, kw_only=True, frozen=True)
class ExportCommand:
    cases: CaseFiles

    def run(self, arguments: ExportArguments) -> int:
        unplanned = arguments.plan is None and sys.stdin.isatty()
        loaded = load_plan('' if unplanned else read_input(arguments.plan))
        if isinstance(loaded, MalformedPlanError):
            raise loaded

        if problem := loaded.get_shape_problem():
            raise problem

        request = ExportRequest(lens=arguments.lens, plan=loaded.parse(), html=arguments.html)
        exported = self.cases.open_press(arguments.case).export(request)
        written = '\n'.join(f'wrote {path}' for path in exported.paths)
        print(written)
        print(f'{exported.lines} of {exported.budget} lines')
        return 0


@dataclass(slots=True, kw_only=True, frozen=True)
class PageCommand:
    cases: CaseFiles

    def run(self, arguments: PageArguments) -> int:
        case = self.cases.open_press(arguments.case).record_page(arguments.url)
        print(f'recorded {case.page_url}')
        return 0


def report_command_problem(*tokens: StrayTokens) -> int:
    problem = f'unknown command "{tokens[0]}"' if tokens else 'a command is required'
    print(f'{PROGRAM}: {problem}; choose from {COMMAND_NAMES}', file=sys.stderr)
    return EXIT_USAGE


def create_app(cases: CaseFiles | None = None) -> App:
    cases = cases or CaseFiles()
    app = App(
        name=PROGRAM,
        help='The red-thread case file.',
        version_flags=(),
        default_parameter=Parameter(negative=()),
        exit_on_error=False,
        print_error=False,
        result_action='return_value',
    )
    app.default(report_command_problem)
    app.command(
        InitCommand(cases=cases).run,
        name='init',
        help='create a case and record what the tree offers',
    )
    app.command(
        AddCommand(cases=cases).run, name='add', help='validate a JSON batch whole, then append it'
    )
    app.command(
        RenderCommand(cases=cases).run,
        name='render',
        help='print the board, with its citations checked',
    )
    app.command(
        CheckCommand(cases=cases).run, name='check', help='resolve every live citation again'
    )
    app.command(
        ExportCommand(cases=cases).run, name='export', help='write a lens output from the ledger'
    )
    app.command(
        PageCommand(cases=cases).run, name='page', help='record the link of the published board'
    )
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
