"""The rungs of a map: full outline, a summary per file, then counts."""

from typing import TYPE_CHECKING

from red_thread_core.dto import DTO

from red_thread_navigate.symbols.domain import FileSymbols, Symbol
from red_thread_navigate.util import plural, rung, span, symbol_address

if TYPE_CHECKING:
    from collections.abc import Sequence

    from red_thread_navigate.symbols.domain import Backends

SUMMARY_NAMES = 3


class RankedSymbol(DTO, frozen=True, kw_only=True, gc=False):
    symbol: Symbol
    references: int


class RankedFile(DTO, frozen=True, kw_only=True, gc=False):
    file: FileSymbols
    symbols: tuple[RankedSymbol, ...]

    @property
    def references(self) -> int:
        return sum(ranked.references for ranked in self.symbols)


def file_line(ranked: RankedFile) -> str:
    path = ranked.file.path
    return f'{path}  {plural(len(ranked.symbols), "symbol")}  {ranked.references} references'


def symbol_line(ranked_file: RankedFile, ranked: RankedSymbol) -> str:
    symbol = ranked.symbol
    address = symbol_address(ranked_file.file.path, symbol)
    label = f'{symbol.kind_label} {symbol.signature}'
    return f'  {label}  {span(symbol)}  {address}  {ranked.references} refs'


def header_line(files: Sequence[RankedFile]) -> str:
    symbols = sum(len(ranked.symbols) for ranked in files)
    return f'{plural(len(files), "file")}  {plural(symbols, "symbol")}'


def outline_lines(ranked_file: RankedFile) -> tuple[str, ...]:
    symbols = (symbol_line(ranked_file, ranked) for ranked in ranked_file.symbols)
    return (file_line(ranked_file), *symbols)


def full_rung(files: Sequence[RankedFile]) -> tuple[str, ...]:
    return rung(header_line(files), *map(outline_lines, files))


def summary_line(ranked_file: RankedFile) -> str:
    names = ', '.join(ranked.symbol.name for ranked in ranked_file.symbols[:SUMMARY_NAMES])
    rest = len(ranked_file.symbols) - SUMMARY_NAMES
    tail = f', and {rest} more' if rest > 0 else ''
    return f'{file_line(ranked_file)}  {names}{tail}' if names else file_line(ranked_file)


def summary_rung(files: Sequence[RankedFile]) -> tuple[str, ...]:
    return rung(header_line(files), map(summary_line, files))


def counts_rung(files: Sequence[RankedFile]) -> tuple[str, ...]:
    return rung(header_line(files), map(file_line, files))


def map_rungs(files: Sequence[RankedFile]) -> tuple[tuple[str, ...], ...]:
    return (full_rung(files), summary_rung(files), counts_rung(files))


def reads_line(backends: Backends) -> str:
    reads = '; '.join(
        f'{backend.language} ({", ".join(sorted(backend.suffixes))})'
        for backend in backends.available()
    )
    return f'navigate reads {reads}.'


def empty_lines(target: str, backends: Backends) -> tuple[str, ...]:
    return (
        f'No file navigate can read under {target}.',
        reads_line(backends),
        'Next step: map a directory or a file with one of those suffixes.',
    )
