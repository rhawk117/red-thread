"""The navigate command line: parse the arguments, run one verb and print its output."""

import argparse
import sys
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import NoReturn, override

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


class UsageError(ValueError):
    def __init__(self, *, problem: str) -> None:
        super().__init__(f'{problem}; valid options are {VALID_OPTIONS}')


class EmptyPathError(UsageError):
    def __init__(self, *, verb: str) -> None:
        super().__init__(problem=f'{verb} needs a PATH that is not empty')


class BudgetTooSmallError(UsageError):
    def __init__(self, *, budget: int) -> None:
        super().__init__(problem=f'--budget {budget} is below the minimum of {MIN_BUDGET} tokens')


@dataclass(slots=True, kw_only=True, frozen=True)
class Request:
    verb: str
    budget: int
    target: str
    path: str | None = None


class Parser(argparse.ArgumentParser):
    @override
    def error(self, message: str) -> NoReturn:
        raise UsageError(problem=message)


def build_parser() -> Parser:
    parser = Parser(prog=PROGRAM, allow_abbrev=False)
    parser.add_argument('--version', action='store_true', help='print the version and exit')
    parser.add_argument(
        '--budget',
        type=int,
        default=DEFAULT_BUDGET,
        metavar='N',
        help=f'the most tokens to print, at least {MIN_BUDGET} (default {DEFAULT_BUDGET})',
    )
    verbs = parser.add_subparsers(dest='verb', metavar='VERB')
    verbs.add_parser('map', help='list the files and symbols under PATH').add_argument('target')
    finder = verbs.add_parser('find', help='list the definitions and references of NAME under PATH')
    finder.add_argument('target', metavar='NAME')
    finder.add_argument('path', metavar='PATH')
    verbs.add_parser('slice', help='print the code ADDRESS names').add_argument(
        'target', metavar='ADDRESS'
    )
    return parser


def parse_request(argv: list[str]) -> Request:
    parsed = build_parser().parse_args(argv)
    if parsed.version:
        return Request(verb='version', budget=DEFAULT_BUDGET, target='')
    if parsed.verb is None:
        message = 'a verb is required: map, find or slice'
        raise UsageError(problem=message)
    if parsed.budget < MIN_BUDGET:
        raise BudgetTooSmallError(budget=parsed.budget)
    path = getattr(parsed, 'path', None)
    searched = path if parsed.verb == 'find' else parsed.target
    if parsed.verb != 'slice' and not searched:
        raise EmptyPathError(verb=parsed.verb)
    return Request(
        verb=parsed.verb,
        budget=parsed.budget,
        target=parsed.target,
        path=path,
    )


def create_navigator() -> Navigator:
    return Navigator(tree=DiskTree(), backends=RegistryBackends())


@dataclass(slots=True, kw_only=True, frozen=True)
class VerbRunner:
    navigator: Navigator
    request: Request

    def show_version(self) -> str:
        return f'{PROGRAM} {version("red-thread-navigate")}'

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
        'version': runner.show_version,
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
    return navigate(create_navigator(), request)
