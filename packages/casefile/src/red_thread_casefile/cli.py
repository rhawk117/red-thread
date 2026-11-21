"""The command line that skills and agents call: init, add, render, check, export and page."""

import sys
from argparse import ArgumentParser
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol, Self, runtime_checkable

from red_thread_casefile.domain import CASE_KINDS, build_case_id
from red_thread_casefile.errors import CaseFileError, MalformedPlanError, UnreadableInputError
from red_thread_casefile.factory import CaseFiles
from red_thread_casefile.lenses import LENS_NAMES
from red_thread_casefile.schemas import load_plan, parse_batch
from red_thread_casefile.services import Batch, ExportRequest, Framing
from red_thread_casefile.views import BoardOptions, CheckReport

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Sequence

type CommandName = Literal['init', 'add', 'render', 'check', 'export', 'page']
type Commands = dict[CommandName, Command]


def read_input(path: str | None) -> str:
    if path is None:
        return str(sys.stdin.read())
    try:
        return Path(path).read_text(encoding='utf-8')
    except OSError as error:
        reason = error.strerror or 'the system gave no reason'
        raise UnreadableInputError(path=path, reason=reason) from error


@runtime_checkable
class Command(Protocol):
    def run(self, arguments: Namespace) -> int: ...


@dataclass(slots=True, kw_only=True, frozen=True)
class InitCommand:
    cases: CaseFiles

    def run(self, arguments: Namespace) -> int:
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
        navigation = 'installed' if case.capabilities.navigation_tool else 'not installed'
        print(f'created {directory.resolve()}')
        print(f'languages: {languages}')
        print(f'navigation tool: {navigation}')
        return 0


@dataclass(slots=True, kw_only=True, frozen=True)
class AddCommand:
    cases: CaseFiles

    def run(self, arguments: Namespace) -> int:
        parsed = parse_batch(read_input(arguments.file))
        batch = Batch(
            drafts=parsed.drafts,
            problems=parsed.problems,
            round=arguments.round,
            thread=arguments.thread,
        )
        added = self.cases.bind(Path(arguments.case)).add(batch)
        refs = ' '.join(entry.ref for entry in added.entries)
        print(f'stored {refs}')
        if added.redactions:
            print(f'redacted {added.redactions} secrets before storing')
        return 0


@dataclass(slots=True, kw_only=True, frozen=True)
class RenderCommand:
    cases: CaseFiles

    def run(self, arguments: Namespace) -> int:
        directory = Path(arguments.case)
        options = BoardOptions.full() if arguments.full else BoardOptions()
        print(self.cases.bind(directory).show(options))
        if arguments.html:
            print(f'wrote {self.cases.open_press(directory).draw()}')
        return 0


@dataclass(slots=True, kw_only=True, frozen=True)
class CheckCommand:
    cases: CaseFiles

    def run(self, arguments: Namespace) -> int:
        report = CheckReport(findings=self.cases.bind(Path(arguments.case)).check())
        print(report.render())
        return int(report.has_failures)


@dataclass(slots=True, kw_only=True, frozen=True)
class ExportCommand:
    cases: CaseFiles

    def run(self, arguments: Namespace) -> int:
        unplanned = arguments.plan is None and sys.stdin.isatty()
        loaded = load_plan('' if unplanned else read_input(arguments.plan))
        if isinstance(loaded, MalformedPlanError):
            raise loaded

        if problem := loaded.get_shape_problem():
            raise problem

        request = ExportRequest(lens=arguments.lens, plan=loaded.parse(), html=arguments.html)
        exported = self.cases.open_press(Path(arguments.case)).export(request)
        written = '\n'.join(f'wrote {path}' for path in exported.paths)
        print(written)
        print(f'{exported.lines} of {exported.budget} lines')
        return 0


@dataclass(slots=True, kw_only=True, frozen=True)
class PageCommand:
    cases: CaseFiles

    def run(self, arguments: Namespace) -> int:
        case = self.cases.open_press(Path(arguments.case)).record_page(arguments.url)
        print(f'recorded {case.page_url}')
        return 0


@dataclass(slots=True, kw_only=True, frozen=True)
class CommandRouter:
    commands: Commands = field(default_factory=dict)

    def mount(self, commands: Commands) -> Self:
        self.commands.update(commands)
        return self

    def dispatch(self, name: CommandName, arguments: Namespace) -> int:
        return self.commands[name].run(arguments)


def create_command_router(cases: CaseFiles | None = None) -> CommandRouter:
    cases = cases or CaseFiles()
    return CommandRouter().mount({
        'init': InitCommand(cases=cases),
        'add': AddCommand(cases=cases),
        'render': RenderCommand(cases=cases),
        'check': CheckCommand(cases=cases),
        'export': ExportCommand(cases=cases),
        'page': PageCommand(cases=cases),
    })


def add_case_argument(parser: ArgumentParser) -> None:
    parser.add_argument('--case', required=True, help='the case directory that init printed')


def describe_init(parser: ArgumentParser) -> None:
    parser.add_argument(
        '--root', default='.', help='the repository root, by default this directory'
    )
    parser.add_argument('--target', required=True, help='the question, as one line')
    parser.add_argument('--kind', required=True, choices=CASE_KINDS, help='the kind of case')
    parser.add_argument('--bar', required=True, help='what the answer must establish')
    parser.add_argument('--slug', help='words for the case id, by default taken from the target')
    parser.add_argument('--publish', action='store_true', help='the owner chose a published page')


def describe_add(parser: ArgumentParser) -> None:
    add_case_argument(parser)
    parser.add_argument('--round', required=True, type=int, help='0 for framing, then the round')
    parser.add_argument('--thread', help='the thread a lead writes to, such as T1')
    parser.add_argument('--file', help='read the batch from this file instead of standard input')


def describe_render(parser: ArgumentParser) -> None:
    add_case_argument(parser)
    parser.add_argument('--full', action='store_true', help='show every live entry')
    parser.add_argument('--html', action='store_true', help='also write board.html in the case')


def describe_export(parser: ArgumentParser) -> None:
    add_case_argument(parser)
    parser.add_argument('--lens', required=True, choices=LENS_NAMES, help='the output to write')
    parser.add_argument('--plan', help='read the plan from this file instead of standard input')
    parser.add_argument('--html', action='store_true', help='also write the output as a page')


def describe_page(parser: ArgumentParser) -> None:
    add_case_argument(parser)
    parser.add_argument('--url', required=True, help='the https link that publishing returned')


def create_parser() -> ArgumentParser:
    parser = ArgumentParser(prog='casefile', description='The red-thread case file.')
    commands = parser.add_subparsers(dest='command', required=True)
    describe_init(commands.add_parser('init', help='create a case and record what the tree offers'))
    describe_add(commands.add_parser('add', help='validate a JSON batch whole, then append it'))
    describe_render(commands.add_parser('render', help='print the board'))
    add_case_argument(commands.add_parser('check', help='resolve every live citation again'))
    describe_export(commands.add_parser('export', help='write a lens output from the ledger'))
    describe_page(commands.add_parser('page', help='record the link of the published board'))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = create_parser().parse_args(argv)
    try:
        return create_command_router().dispatch(arguments.command, arguments)
    except CaseFileError as error:
        print(f'casefile: {error}', file=sys.stderr)
        return 1
