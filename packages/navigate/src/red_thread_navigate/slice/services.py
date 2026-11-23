"""Slicing an address: read the one file, find the target and fit the result to a budget."""

import re
from difflib import get_close_matches
from typing import TYPE_CHECKING

from red_thread_navigate.address import LineTarget, SymbolTarget, parse_address
from red_thread_navigate.budget import estimate_tokens, fit_to_budget
from red_thread_navigate.slice.views import Found, line_rungs, symbol_rungs
from red_thread_navigate.symbols.store import backend_for
from red_thread_navigate.walk import SourceFile
from red_thread_navigate.walk.store import read_source

if TYPE_CHECKING:
    from pathlib import Path, PurePosixPath

    from red_thread_navigate.symbols.domain import FileSymbols, Symbol

WINDOW_LINES = 100
NEAREST_NAMES = 5
LINE_BREAK = re.compile(r'\r\n|\r|\n')


class SliceError(ValueError):
    """Base of every refusal the slice verb makes."""


class FileRefusedError(SliceError):
    def __init__(self, *, path: PurePosixPath, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f'{path} cannot be sliced: {reason}')


class UnknownSymbolError(SliceError):
    def __init__(self, *, path: PurePosixPath, name: str, nearest: tuple[str, ...]) -> None:
        self.path = path
        self.name = name
        self.nearest = nearest
        hint = f'nearest names: {", ".join(nearest)}' if nearest else 'the file has no similar name'
        super().__init__(f'no symbol {name!r} in {path}; {hint}')


class LinesOutOfRangeError(SliceError):
    def __init__(self, *, path: PurePosixPath, start: int, total: int) -> None:
        self.path = path
        self.start = start
        self.total = total
        super().__init__(f'{path} has {total} lines, so L{start} is past its end')


def read_file(root: Path, path: PurePosixPath) -> SourceFile:
    source = read_source(root, root.joinpath(path), path)
    if isinstance(source, SourceFile):
        return source
    reasons = {
        None: 'it is not a file',
        'outside_root': 'it resolves outside the root',
        'too_large': 'it is over 1 MiB',
        'binary': 'it is binary',
        'not_utf8': 'it is not UTF-8',
        'unreadable': 'it cannot be read',
    }
    raise FileRefusedError(path=path, reason=reasons[source])


def split_lines(text: str) -> tuple[str, ...]:
    lines = [str(line) for line in LINE_BREAK.split(text)]
    if lines and not lines[-1]:
        lines.pop()
    return tuple(lines)


def slice_lines(source: SourceFile, target: LineTarget, *, budget: int) -> str:
    lines = split_lines(source.text)
    if target.start > len(lines):
        raise LinesOutOfRangeError(path=source.path, start=target.start, total=len(lines))
    chosen = lines[target.start - 1 : target.end]
    rungs = line_rungs(source.path, start=target.start, lines=chosen)
    return fit_to_budget(rungs, budget=budget).text


def parse_file(source: SourceFile) -> FileSymbols:
    backend = backend_for(source.path)
    if backend is None:
        reason = (
            f'no symbol backend reads {source.path.suffix or "this"} files, '
            f'address lines instead, such as {source.path}#L1-L20'
        )
        raise FileRefusedError(path=source.path, reason=reason)
    return backend.parse(source)


def found_for(source: SourceFile, symbol: Symbol, parsed: FileSymbols) -> Found:
    lines = split_lines(source.text)
    children = tuple(child for child in parsed.symbols if child.parent == symbol.qualified_name)
    return Found(
        path=source.path,
        symbol=symbol,
        children=children,
        lines=lines[symbol.start_line - 1 : symbol.end_line],
        whole=symbol.end_line - symbol.start_line + 1 <= WINDOW_LINES,
    )


def unknown_symbol(parsed: FileSymbols, name: str, *, budget: int) -> UnknownSymbolError:
    names = sorted({symbol.qualified_name for symbol in parsed.symbols})
    nearest = tuple(get_close_matches(name, names, n=NEAREST_NAMES))
    error = UnknownSymbolError(path=parsed.path, name=name, nearest=nearest)
    while nearest and estimate_tokens(str(error)) > budget:
        nearest = nearest[:-1]
        error = UnknownSymbolError(path=parsed.path, name=name, nearest=nearest)
    return error


def slice_symbol(source: SourceFile, target: SymbolTarget, *, budget: int) -> str:
    parsed = parse_file(source)
    name = '.'.join(target.parts)
    matches = tuple(symbol for symbol in parsed.symbols if symbol.qualified_name == name)
    if not matches:
        raise unknown_symbol(parsed, name, budget=budget)
    founds = tuple(found_for(source, symbol, parsed) for symbol in matches)
    return fit_to_budget(symbol_rungs(founds, parsed.notes), budget=budget).text


def slice_address(text: str, *, root: Path, budget: int) -> str:
    """Return the code an address names, inside the budget; refuse what it cannot name."""
    resolved = root.resolve()
    address = parse_address(text, root=resolved)
    source = read_file(resolved, address.path)
    match address.target:
        case LineTarget() as lines:
            return slice_lines(source, lines, budget=budget)
        case SymbolTarget() as symbol:
            return slice_symbol(source, symbol, budget=budget)
