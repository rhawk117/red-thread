"""Slicing an address: read the one file, find the target and fit the result to a budget."""

import re
from dataclasses import dataclass
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


ELLIPSIS = '...'
MIN_SHOWN = 8
PLACEHOLDER = re.compile(r'<path>|<name>')


def shorten_path(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    head = (limit - len(ELLIPSIS)) // 3
    tail = limit - len(ELLIPSIS) - head
    return f'{text[:head]}{ELLIPSIS}{text[-tail:]}'


def shorten_name(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f'{text[: limit - len(ELLIPSIS)]}{ELLIPSIS}'


def fill(template: str, *, path: str, name: str) -> str:
    shown = {'<path>': path, '<name>': name}
    segments = PLACEHOLDER.split(template)
    values = [shown[token] for token in PLACEHOLDER.findall(template)]
    return ''.join(
        f'{segment}{value}' for segment, value in zip(segments, [*values, ''], strict=True)
    )


def refusal_text(template: str, *, refused: Refused, name: str) -> str:
    """Fill <path> and <name>, cutting the longer of the two until the text fits the budget."""
    full_path = str(refused.path)
    budget = refused.budget
    path_limit = len(full_path)
    name_limit = len(name)
    text = fill(template, path=full_path, name=name)
    while budget is not None and estimate_tokens(text) > budget:
        if path_limit >= name_limit and path_limit > MIN_SHOWN:
            path_limit -= 1
        elif name_limit > MIN_SHOWN:
            name_limit -= 1
        else:
            break
        text = fill(
            template,
            path=shorten_path(full_path, path_limit),
            name=shorten_name(name, name_limit),
        )
    return text if budget is None else cut_to_budget(text, budget)


def cut_to_budget(text: str, budget: int) -> str:
    keep = len(text)
    fitted = text
    while estimate_tokens(fitted) > budget and keep > 0:
        keep -= 1
        fitted = f'{text[:keep]}{ELLIPSIS}'
    return fitted


@dataclass(slots=True, kw_only=True, frozen=True)
class Refused:
    """The path a refusal names and the budget its message must fit; no budget leaves it whole."""

    path: PurePosixPath
    budget: int | None = None


class SliceError(ValueError):
    """Base of every refusal the slice verb makes."""


class FileRefusedError(SliceError):
    def __init__(self, *, refused: Refused, reason: str) -> None:
        self.path = refused.path
        self.reason = reason
        template = f'<path> cannot be sliced: {reason}'
        super().__init__(refusal_text(template, refused=refused, name=''))


class UnknownSymbolError(SliceError):
    def __init__(self, *, refused: Refused, name: str, nearest: tuple[str, ...]) -> None:
        self.path = refused.path
        self.name = name
        self.nearest = nearest
        hint = f'nearest names: {", ".join(nearest)}' if nearest else 'the file has no similar name'
        template = f'no symbol <name> in <path>; {hint}'
        super().__init__(refusal_text(template, refused=refused, name=repr(name)))


class LinesOutOfRangeError(SliceError):
    def __init__(self, *, refused: Refused, start: int, total: int) -> None:
        self.path = refused.path
        self.start = start
        self.total = total
        template = f'<path> has {total} lines, so L{start} is past its end'
        super().__init__(refusal_text(template, refused=refused, name=''))


def read_file(root: Path, path: PurePosixPath, *, budget: int) -> SourceFile:
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
    raise FileRefusedError(refused=Refused(path=path, budget=budget), reason=reasons[source])


def split_lines(text: str) -> tuple[str, ...]:
    lines = [str(line) for line in LINE_BREAK.split(text)]
    if lines and not lines[-1]:
        lines.pop()
    return tuple(lines)


def slice_lines(source: SourceFile, target: LineTarget, *, budget: int) -> str:
    lines = split_lines(source.text)
    if target.start > len(lines):
        raise LinesOutOfRangeError(
            refused=Refused(path=source.path, budget=budget), start=target.start, total=len(lines)
        )
    chosen = lines[target.start - 1 : target.end]
    rungs = line_rungs(source.path, start=target.start, lines=chosen)
    return fit_to_budget(rungs, budget=budget).text


def parse_file(source: SourceFile, *, budget: int) -> FileSymbols:
    backend = backend_for(source.path)
    if backend is None:
        suffix = shorten_name(source.path.suffix, MIN_SHOWN) or 'this'
        reason = f'no symbol backend reads {suffix} files, address lines instead, such as #L1-L20'
        raise FileRefusedError(refused=Refused(path=source.path, budget=budget), reason=reason)
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
    whole = Refused(path=parsed.path)
    error = UnknownSymbolError(refused=whole, name=name, nearest=nearest)
    while nearest and estimate_tokens(str(error)) > budget:
        nearest = nearest[:-1]
        error = UnknownSymbolError(refused=whole, name=name, nearest=nearest)
    refused = Refused(path=parsed.path, budget=budget)
    return UnknownSymbolError(refused=refused, name=name, nearest=nearest)


def slice_symbol(source: SourceFile, target: SymbolTarget, *, budget: int) -> str:
    parsed = parse_file(source, budget=budget)
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
    source = read_file(resolved, address.path, budget=budget)
    match address.target:
        case LineTarget() as lines:
            return slice_lines(source, lines, budget=budget)
        case SymbolTarget() as symbol:
            return slice_symbol(source, symbol, budget=budget)
