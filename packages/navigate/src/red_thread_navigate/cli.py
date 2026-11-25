"""The navigate command line: parse the arguments, run one verb and print its output."""

import sys
from dataclasses import dataclass, replace
from importlib.metadata import version
from pathlib import Path
from typing import Annotated, Literal

from cyclopts import App, CycloptsError, Parameter

from red_thread_navigate.address import AddressError
from red_thread_navigate.budget import MIN_BUDGET, cut_to_budget
from red_thread_navigate.services import Navigator
from red_thread_navigate.slice import SliceError
from red_thread_navigate.symbols.store import RegistryBackends
from red_thread_navigate.walk import DiskTree, PathMissingError

PROGRAM = 'red-thread-navigate'
DEFAULT_BUDGET = 2000
VALID_OPTIONS = '--budget N, --version, --help'
EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_USAGE = 2

type VerbName = Literal['map', 'find', 'slice']
type Tokens = Annotated[str, Parameter(show=False, allow_leading_hyphen=True)]
type Budget = Annotated[
    int,
    Parameter(help=f'the most tokens to print, at least {MIN_BUDGET} (default {DEFAULT_BUDGET})'),
]


class UsageError(ValueError):
    def __init__(self, *, problem: str) -> None:
        super().__init__(f'{problem}; valid options are {VALID_OPTIONS}')


class MissingVerbError(UsageError):
    def __init__(self) -> None:
        super().__init__(problem='a verb is required: map, find or slice')


class EmptyPathError(UsageError):
    def __init__(self, *, verb: str) -> None:
        super().__init__(problem=f'{verb} needs a PATH that is not empty')


class BudgetTooSmallError(UsageError):
    def __init__(self, *, budget: int) -> None:
        super().__init__(problem=f'--budget {budget} is below the minimum of {MIN_BUDGET} tokens')


@dataclass(slots=True, kw_only=True, frozen=True)
class Request:
    verb: VerbName
    budget: int = DEFAULT_BUDGET
    target: str
    path: str | None = None

    @property
    def searched(self) -> str:
        return (self.path or '') if self.verb == 'find' else self.target

    def get_usage_problem(self) -> UsageError | None:
        if self.budget < MIN_BUDGET:
            return BudgetTooSmallError(budget=self.budget)

        if self.verb != 'slice' and not self.searched:
            return EmptyPathError(verb=self.verb)

        return None


def request_map(path: str, /) -> Request:
    return Request(verb='map', target=path)


def request_find(name: str, path: str, /) -> Request:
    return Request(verb='find', target=name, path=path)


def request_slice(address: str, /) -> Request:
    return Request(verb='slice', target=address)


def describe_version() -> str:
    return f'{PROGRAM} {version("red-thread-navigate")}'


@dataclass(slots=True, kw_only=True, frozen=True)
class Launcher:
    verbs: App

    def launch(self, *tokens: Tokens, budget: Budget = DEFAULT_BUDGET) -> Request | None:
        if not tokens:
            raise MissingVerbError

        request = self.verbs(tokens)
        if not isinstance(request, Request):
            return None

        request = replace(request, budget=budget)
        if problem := request.get_usage_problem():
            raise problem

        return request


def build_app() -> App:
    verbs = App(
        name=PROGRAM,
        version=describe_version,
        exit_on_error=False,
        print_error=False,
        result_action='return_value',
    )
    verbs.command(request_map, name='map', help='list the files and symbols under PATH')
    verbs.command(
        request_find, name='find', help='list the definitions and references of NAME under PATH'
    )
    verbs.command(request_slice, name='slice', help='print the code ADDRESS names')
    verbs.meta.default(Launcher(verbs=verbs).launch)
    return verbs


def parse_request(argv: list[str]) -> Request | None:
    try:
        parsed = build_app().meta(argv)
    except CycloptsError as error:
        raise UsageError(problem=str(error).rstrip('.')) from error
    return parsed if isinstance(parsed, Request) else None


def create_navigator() -> Navigator:
    return Navigator(tree=DiskTree(), backends=RegistryBackends())


@dataclass(slots=True, kw_only=True, frozen=True)
class VerbRunner:
    navigator: Navigator
    request: Request

    def map_target(self) -> str:
        return self.navigator.map(Path(self.request.target), budget=self.request.budget)

    def find_name(self) -> str:
        path = Path(self.request.path or '')
        return self.navigator.find(self.request.target, path, budget=self.request.budget)

    def slice_address(self) -> str:
        return self.navigator.slice(
            self.request.target, root=Path.cwd(), budget=self.request.budget
        )


def run_verb(navigator: Navigator, request: Request) -> str:
    runner = VerbRunner(navigator=navigator, request=request)
    verbs = {
        'map': runner.map_target,
        'find': runner.find_name,
        'slice': runner.slice_address,
    }
    return verbs[request.verb]()


def navigate(navigator: Navigator, request: Request) -> int:
    try:
        text = run_verb(navigator, request)
    except (SliceError, AddressError, PathMissingError) as refusal:
        print(cut_to_budget(str(refusal), request.budget), file=sys.stderr)
        return EXIT_REFUSED
    print(cut_to_budget(text, request.budget))
    return EXIT_OK


def run(argv: list[str]) -> int:
    try:
        request = parse_request(argv)
    except UsageError as error:
        print(f'{PROGRAM}: {error}', file=sys.stderr)
        return EXIT_USAGE

    if request is None:
        return EXIT_OK

    return navigate(create_navigator(), request)
