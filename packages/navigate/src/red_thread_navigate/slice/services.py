"""Slicing an address: read the one file, find the target and fit the result to a budget."""

import re
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from red_thread_navigate.address import (
    AddressError,
    LineTarget,
    MalformedAddressError,
    SymbolTarget,
    parse_address,
)
from red_thread_navigate.budget import estimate_tokens, fit_to_budget
from red_thread_navigate.slice.views import Found, line_rungs, symbol_rungs
from red_thread_navigate.symbols.store import backend_for
from red_thread_navigate.walk import SourceFile
from red_thread_navigate.walk.store import read_source

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from red_thread_navigate.symbols.domain import FileSymbols, Symbol

WINDOW_LINES = 100
NEAREST_NAMES = 5
LINE_BREAK = re.compile(r'\r\n|\r|\n')


ELLIPSIS = '...'
MIN_SHOWN = 8
FILE_NAME_FLOOR = 20
PLACEHOLDER = re.compile(r'<path>|<name>')


def shorten_path(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f'{ELLIPSIS}{text[len(ELLIPSIS) - limit :]}'


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


def cut_steps(full_path: str, name: str, *, deep: bool) -> Iterator[tuple[int, int]]:
    file_name = PurePosixPath(full_path).name
    floor = min(
        len(full_path), max(MIN_SHOWN, min(len(file_name), FILE_NAME_FLOOR) + len(ELLIPSIS))
    )
    name_floor = min(len(name), MIN_SHOWN)
    yield from ((limit, len(name)) for limit in range(len(full_path), floor - 1, -1))
    yield from ((floor, limit) for limit in range(len(name), name_floor - 1, -1))
    if deep:
        yield from ((limit, name_floor) for limit in range(floor, MIN_SHOWN - 1, -1))


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


@dataclass(slots=True, kw_only=True, frozen=True)
class Wording:
    template: str
    refused: Refused
    name: str

    def fit(self, *, deep: bool) -> str | None:
        full_path = str(self.refused.path)
        budget = self.refused.budget
        if budget is None:
            return fill(self.template, path=full_path, name=self.name)
        texts = (
            fill(
                self.template,
                path=shorten_path(full_path, path_limit),
                name=shorten_name(self.name, name_limit),
            )
            for path_limit, name_limit in cut_steps(full_path, self.name, deep=deep)
        )
        return next((text for text in texts if estimate_tokens(text) <= budget), None)

    def text(self) -> str:
        if (fitted := self.fit(deep=True)) is not None:
            return fitted
        shown = fill(
            self.template,
            path=shorten_path(str(self.refused.path), MIN_SHOWN),
            name=shorten_name(self.name, MIN_SHOWN),
        )
        return cut_to_budget(shown, self.refused.budget or 0)


def refusal_text(template: str, *, refused: Refused, name: str) -> str:
    return Wording(template=template, refused=refused, name=name).text()


def unknown_template(nearest: tuple[str, ...], *, mapped: bool = False) -> str:
    hint = f'nearest names: {", ".join(nearest)}' if nearest else 'the file has no similar name'
    next_step = '. Next step: map <path> to see the names there.' if mapped else ''
    return f'no symbol <name> in <path>; {hint}{next_step}'


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
        template = unknown_template(nearest)
        if not nearest:
            mapped = unknown_template(nearest, mapped=True)
            wording = Wording(template=mapped, refused=refused, name=repr(name))
            template = mapped if wording.fit(deep=False) is not None else template
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
        reason = f'no symbol backend reads {suffix} files, use lines like #L1-L20'
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


def nearest_candidates(nearest: tuple[str, ...]) -> Iterator[tuple[str, ...]]:
    counts = range(len(nearest), 0, -1)
    yield from (nearest[:count] for count in counts)
    longest = max(map(len, nearest), default=0)
    for count in counts:
        yield from (
            tuple(shorten_name(item, limit) for item in nearest[:count])
            for limit in range(longest, MIN_SHOWN - 1, -1)
        )


def unknown_symbol(parsed: FileSymbols, name: str, *, budget: int) -> UnknownSymbolError:
    names = sorted({symbol.qualified_name for symbol in parsed.symbols})
    nearest = tuple(get_close_matches(name, names, n=NEAREST_NAMES))
    refused = Refused(path=parsed.path, budget=budget)
    shown = next(
        (
            candidate
            for candidate in nearest_candidates(nearest)
            if Wording(template=unknown_template(candidate), refused=refused, name=repr(name)).fit(
                deep=False
            )
            is not None
        ),
        (),
    )
    return UnknownSymbolError(refused=refused, name=name, nearest=shown)


def slice_symbol(source: SourceFile, target: SymbolTarget, *, budget: int) -> str:
    parsed = parse_file(source, budget=budget)
    name = '.'.join(target.parts)
    matches = tuple(symbol for symbol in parsed.symbols if symbol.qualified_name == name)
    if not matches:
        raise unknown_symbol(parsed, name, budget=budget)
    founds = tuple(found_for(source, symbol, parsed) for symbol in matches)
    return fit_to_budget(symbol_rungs(founds, parsed.notes), budget=budget).text


def address_refusal(text: str, error: AddressError, *, budget: int) -> FileRefusedError:
    reason = (
        error.reason if isinstance(error, MalformedAddressError) else 'it reaches outside the root'
    )
    return FileRefusedError(refused=Refused(path=PurePosixPath(text), budget=budget), reason=reason)


def slice_address(text: str, *, root: Path, budget: int) -> str:
    """Return the code an address names, inside the budget; refuse what it cannot name."""
    resolved = root.resolve()
    try:
        address = parse_address(text, root=resolved)
    except AddressError as error:
        if estimate_tokens(str(error)) <= budget:
            raise
        raise address_refusal(text, error, budget=budget) from error
    source = read_file(resolved, address.path, budget=budget)
    match address.target:
        case LineTarget() as lines:
            return slice_lines(source, lines, budget=budget)
        case SymbolTarget() as symbol:
            return slice_symbol(source, symbol, budget=budget)
