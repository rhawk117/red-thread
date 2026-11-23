"""The navigate command line: parse the arguments, run one verb and print its output."""

import argparse
import sys
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import NoReturn, override

from red_thread_navigate.address import AddressError
from red_thread_navigate.budget import MIN_BUDGET, cut_to_budget
from red_thread_navigate.find.services import find_name
from red_thread_navigate.map.services import map_path
from red_thread_navigate.slice import SliceError, slice_address

PROGRAM = 'red-thread-navigate'
DEFAULT_BUDGET = 2000
VALID_OPTIONS = '--budget N, --version, --help'
EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_USAGE = 2


class UsageError(ValueError):
    """The command line is not one navigate accepts."""

    def __init__(self, *, problem: str) -> None:
        super().__init__(f'{problem}; valid options are {VALID_OPTIONS}')


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


def parse_request(argv: list[str]) -> Request | None:
    """Return the request, or None when the arguments ask for the version."""
    parsed = build_parser().parse_args(argv)
    if parsed.version:
        return None
    if parsed.verb is None:
        message = 'a verb is required: map, find or slice'
        raise UsageError(problem=message)
    if parsed.budget < MIN_BUDGET:
        raise BudgetTooSmallError(budget=parsed.budget)
    return Request(
        verb=parsed.verb,
        budget=parsed.budget,
        target=parsed.target,
        path=getattr(parsed, 'path', None),
    )


def run_verb(request: Request) -> str:
    match request.verb:
        case 'map':
            return map_path(Path(request.target), budget=request.budget)
        case 'find':
            return find_name(request.target, Path(request.path or '.'), budget=request.budget)
        case _:
            return slice_address(request.target, root=Path.cwd(), budget=request.budget)


def navigate(request: Request) -> int:
    try:
        text = run_verb(request)
    except (SliceError, AddressError) as refusal:
        print(cut_to_budget(str(refusal), request.budget), file=sys.stderr)
        return EXIT_REFUSED
    print(cut_to_budget(text, request.budget))
    return EXIT_OK


def run(argv: list[str]) -> int:
    """Run the navigate command line over argv and return its exit code."""
    try:
        request = parse_request(argv)
    except UsageError as error:
        print(f'{PROGRAM}: {error}', file=sys.stderr)
        return EXIT_USAGE
    if request is None:
        print(f'{PROGRAM} {version("red-thread-navigate")}')
        return EXIT_OK
    return navigate(request)
