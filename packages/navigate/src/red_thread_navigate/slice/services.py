"""Slicing an address: read the one file, find the target and fit the result to a budget."""

from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from red_thread_navigate.address import (
    AddressError,
    LineTarget,
    MalformedAddressError,
    OutsideRootError,
    parse_address,
)
from red_thread_navigate.budget import estimate_tokens, fit_text
from red_thread_navigate.slice.errors import (
    FileRefusedError,
    HintedOutsideRootError,
    LinesOutOfRangeError,
    UnknownSymbolError,
)
from red_thread_navigate.slice.policy import (
    MAP_HINT,
    OUTSIDE_ROOT_HINT,
    Refused,
    file_refused_text,
    fitted_nearest,
    lines_out_of_range_text,
    outside_root_text,
    unknown_symbol_text,
)
from red_thread_navigate.slice.util import MIN_SHOWN, shorten
from red_thread_navigate.slice.views import Found, line_rungs, symbol_rungs
from red_thread_navigate.util import split_lines
from red_thread_navigate.walk import SKIP_LABELS, SourceFile

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_navigate.address import (
        SymbolTarget,
    )
    from red_thread_navigate.symbols.domain import Backends, FileSymbols, Symbol
    from red_thread_navigate.walk import SkipKind, SourceTree

WINDOW_LINES = 100
NEAREST_NAMES = 5


def refuse_file(*, refused: Refused, reason: str, hint: str = '') -> FileRefusedError:
    message = file_refused_text(refused=refused, reason=reason, hint=hint)
    return FileRefusedError(path=refused.path, reason=reason, message=message)


def slice_lines(source: SourceFile, target: LineTarget, *, budget: int) -> str:
    lines = split_lines(source.text)
    if target.start > len(lines):
        refused = Refused(path=source.path, budget=budget)
        message = lines_out_of_range_text(refused=refused, start=target.start, total=len(lines))
        raise LinesOutOfRangeError(start=target.start, total=len(lines), message=message)
    chosen = lines[target.start - 1 : target.end]
    rungs = line_rungs(source.path, start=target.start, lines=chosen)
    return fit_text(rungs, budget=budget)


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
    refused = Refused(path=parsed.path, budget=budget)
    shown = fitted_nearest(refused=refused, name=name, nearest=nearest)
    message = unknown_symbol_text(refused=refused, name=name, nearest=shown)
    return UnknownSymbolError(name=name, nearest=shown, message=message)


def hinted_outside_root(error: AddressError, *, budget: int) -> HintedOutsideRootError | None:
    if not isinstance(error, OutsideRootError):
        return None
    message = outside_root_text(str(error), budget=budget)
    if message is None:
        return None
    return HintedOutsideRootError(text=error.text, root=error.root, message=message)


def address_refusal(text: str, error: AddressError, *, budget: int) -> FileRefusedError:
    refused = Refused(path=PurePosixPath(text), budget=budget)
    if isinstance(error, MalformedAddressError):
        return refuse_file(refused=refused, reason=error.reason)
    return refuse_file(
        refused=refused, reason='it reaches outside the root', hint=OUTSIDE_ROOT_HINT
    )


def explain_address_error(
    text: str, error: AddressError, *, budget: int
) -> HintedOutsideRootError | FileRefusedError | None:
    if hinted := hinted_outside_root(error, budget=budget):
        return hinted

    if estimate_tokens(str(error)) <= budget:
        return None

    return address_refusal(text, error, budget=budget)


@dataclass(slots=True, kw_only=True, frozen=True)
class Slicer:
    tree: SourceTree
    backends: Backends

    def read_file(self, root: Path, path: PurePosixPath, *, budget: int) -> SourceFile:
        source = self.tree.read(root, path)
        if isinstance(source, SourceFile):
            return source
        hints: dict[SkipKind, str] = {
            'not_a_file': MAP_HINT,
            'outside_root': OUTSIDE_ROOT_HINT,
        }
        refused = Refused(path=path, budget=budget)
        reason = SKIP_LABELS[source].reason
        raise refuse_file(refused=refused, reason=reason, hint=hints.get(source, ''))

    def parse_file(self, source: SourceFile, *, budget: int) -> FileSymbols:
        backend = self.backends.for_path(source.path)
        if not backend:
            suffix = shorten(source.path.suffix, MIN_SHOWN, keep='head') or 'this'
            reason = f'no symbol backend reads {suffix} files, use lines like #L1-L20'
            raise refuse_file(refused=Refused(path=source.path, budget=budget), reason=reason)
        return backend.parse(source)

    def slice_symbol(self, source: SourceFile, target: SymbolTarget, *, budget: int) -> str:
        parsed = self.parse_file(source, budget=budget)
        name = '.'.join(target.parts)
        matches = tuple(symbol for symbol in parsed.symbols if symbol.qualified_name == name)
        if not matches:
            raise unknown_symbol(parsed, name, budget=budget)
        founds = tuple(found_for(source, symbol, parsed) for symbol in matches)
        return fit_text(symbol_rungs(founds, parsed.notes, budget=budget), budget=budget)

    def slice_address(self, text: str, *, root: Path, budget: int) -> str:
        resolved = root.resolve()
        try:
            address = parse_address(text, root=resolved)
        except AddressError as error:
            if (replacement := explain_address_error(text, error, budget=budget)) is None:
                raise
            raise replacement from error
        source = self.read_file(resolved, address.path, budget=budget)
        if isinstance(address.target, LineTarget):
            return slice_lines(source, address.target, budget=budget)
        return self.slice_symbol(source, address.target, budget=budget)
