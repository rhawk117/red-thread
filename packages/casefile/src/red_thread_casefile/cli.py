"""The command line that skills and agents call: init, render, check and export."""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

from cyclopts import Parameter
from red_thread_core.cli import EXIT_OK, run_app
from red_thread_core.cli import create_app as create_shared_app

from red_thread_casefile.domain import (
    CASE_FILE,
    PROGRAM,
    STATE_DIRECTORY,
    CaseKind,
    build_case_id,
)
from red_thread_casefile.errors import MalformedSelectionError, UnreadableInputError
from red_thread_casefile.factory import CaseFiles
from red_thread_casefile.lenses import LensName
from red_thread_casefile.schemas import load_selection
from red_thread_casefile.services import ExportRequest, Framing
from red_thread_casefile.views import BoardOptions, CheckReport

if TYPE_CHECKING:
    from collections.abc import Sequence

    from cyclopts import App

type CaseOption = Annotated[Path, Parameter(help='the case directory that init printed')]
type RootOption = Annotated[str, Parameter(help='the repository root, by default this directory')]
type TargetOption = Annotated[str, Parameter(help='the question, as one line')]
type KindOption = Annotated[CaseKind, Parameter(help='the kind of case')]
type BarOption = Annotated[str, Parameter(help='what the answer must establish')]
type SlugOption = Annotated[
    str | None, Parameter(help='words for the case id, by default taken from the target')
]
type PublishFlag = Annotated[bool, Parameter(help='the owner chose a published page')]
type FullFlag = Annotated[bool, Parameter(help='show every live entry')]
type BoardFlag = Annotated[bool, Parameter(help='also write board.html in the case')]
type LensOption = Annotated[LensName, Parameter(help='the output to write')]
type SelectionOption = Annotated[
    str | None, Parameter(help='read the selection from this file instead of standard input')
]
type PageFlag = Annotated[bool, Parameter(help='also write the output as a page')]


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
class RenderArguments:
    case: CaseOption
    full: FullFlag = False
    html: BoardFlag = False


@Parameter(name='*')
@dataclass(slots=True, kw_only=True, frozen=True)
class ExportArguments:
    case: CaseOption
    lens: LensOption
    selection: SelectionOption = None
    html: PageFlag = False


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
    name: str = 'init'
    summary: str = 'write case.md with its frontmatter and the round 0 heading'

    def run(self, arguments: InitArguments) -> int:
        case_id = build_case_id(self.cases.clock.now(), arguments.slug or arguments.target)
        directory = Path(arguments.root).joinpath(STATE_DIRECTORY, case_id)
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
        print(f'write entries in {directory.resolve().joinpath(CASE_FILE)}, then run check')
        return EXIT_OK


@dataclass(slots=True, kw_only=True, frozen=True)
class RenderCommand:
    cases: CaseFiles
    name: str = 'render'
    summary: str = 'print the board, with its citations checked'

    def run(self, arguments: RenderArguments) -> int:
        directory = arguments.case
        options = BoardOptions.full() if arguments.full else BoardOptions()
        print(self.cases.bind(directory).show(options))
        if arguments.html:
            print(f'wrote {self.cases.open_press(directory).draw()}')
        return EXIT_OK


@dataclass(slots=True, kw_only=True, frozen=True)
class CheckCommand:
    cases: CaseFiles
    name: str = 'check'
    summary: str = 'report every fault in the case and its citations; writes nothing'

    def run(self, arguments: CaseArguments) -> int:
        checked = self.cases.bind(arguments.case).check()
        report = CheckReport(findings=checked.findings, problems=checked.problems)
        print(report.render())
        return int(report.has_failures)


@dataclass(slots=True, kw_only=True, frozen=True)
class ExportCommand:
    cases: CaseFiles
    name: str = 'export'
    summary: str = 'write a lens output from the ledger'

    def run(self, arguments: ExportArguments) -> int:
        unselected = arguments.selection is None and sys.stdin.isatty()
        loaded = load_selection('' if unselected else read_input(arguments.selection))
        if isinstance(loaded, MalformedSelectionError):
            raise loaded

        if problem := loaded.get_shape_problem():
            raise problem

        request = ExportRequest(lens=arguments.lens, selection=loaded.parse(), html=arguments.html)
        exported = self.cases.open_press(arguments.case).export(request)
        written = '\n'.join(f'wrote {path}' for path in exported.paths)
        print(written)
        print(f'{exported.lines} of {exported.budget} lines')
        return EXIT_OK


def create_app(cases: CaseFiles | None = None) -> App:
    cases = cases or CaseFiles()
    commands = (
        InitCommand(cases=cases),
        RenderCommand(cases=cases),
        CheckCommand(cases=cases),
        ExportCommand(cases=cases),
    )
    return create_shared_app(PROGRAM, 'The red-thread case file.', commands)


def main(argv: Sequence[str] | None = None) -> int:
    return run_app(PROGRAM, create_app(), argv)
