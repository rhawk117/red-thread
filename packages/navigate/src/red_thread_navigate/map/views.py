"""The rungs of a map: full outline, a summary per file, then counts."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_navigate.symbols.store import BACKENDS

if TYPE_CHECKING:
    from red_thread_navigate.symbols.domain import FileSymbols, Symbol

SUMMARY_NAMES = 3


@dataclass(slots=True, kw_only=True, frozen=True)
class RankedSymbol:
    symbol: Symbol
    references: int


@dataclass(slots=True, kw_only=True, frozen=True)
class RankedFile:
    file: FileSymbols
    symbols: tuple[RankedSymbol, ...]

    @property
    def references(self) -> int:
        return sum(ranked.references for ranked in self.symbols)


def span(symbol: Symbol) -> str:
    if symbol.end_line == symbol.start_line:
        return f'L{symbol.start_line}'
    return f'L{symbol.start_line}-L{symbol.end_line}'


def plural(count: int, noun: str) -> str:
    return f'{count} {noun}' if count == 1 else f'{count} {noun}s'


def file_line(ranked: RankedFile) -> str:
    path = ranked.file.path
    return f'{path}  {plural(len(ranked.symbols), "symbol")}  {ranked.references} references'


def symbol_line(ranked_file: RankedFile, ranked: RankedSymbol) -> str:
    symbol = ranked.symbol
    address = f'{ranked_file.file.path}#{symbol.qualified_name}'
    return (
        f'  {symbol.kind} {symbol.signature}  {span(symbol)}  {address}  {ranked.references} refs'
    )


def header_line(files: tuple[RankedFile, ...]) -> str:
    symbols = sum(len(ranked.symbols) for ranked in files)
    return f'{plural(len(files), "file")}  {plural(symbols, "symbol")}'


def full_rung(files: tuple[RankedFile, ...]) -> tuple[str, ...]:
    lines = [header_line(files)]
    for ranked_file in files:
        lines.append(file_line(ranked_file))
        lines.extend(symbol_line(ranked_file, ranked) for ranked in ranked_file.symbols)
    return tuple(lines)


def summary_line(ranked_file: RankedFile) -> str:
    names = ', '.join(ranked.symbol.name for ranked in ranked_file.symbols[:SUMMARY_NAMES])
    rest = len(ranked_file.symbols) - SUMMARY_NAMES
    tail = f', and {rest} more' if rest > 0 else ''
    return f'{file_line(ranked_file)}  {names}{tail}' if names else file_line(ranked_file)


def summary_rung(files: tuple[RankedFile, ...]) -> tuple[str, ...]:
    return (header_line(files), *(summary_line(ranked_file) for ranked_file in files))


def counts_rung(files: tuple[RankedFile, ...]) -> tuple[str, ...]:
    return (header_line(files), *(file_line(ranked_file) for ranked_file in files))


def map_rungs(files: tuple[RankedFile, ...]) -> tuple[tuple[str, ...], ...]:
    return (full_rung(files), summary_rung(files), counts_rung(files))


def reads_line() -> str:
    reads = '; '.join(
        f'{backend.language} ({", ".join(sorted(backend.suffixes))})' for backend in BACKENDS
    )
    return f'navigate reads {reads}.'


def empty_lines(target: str) -> tuple[str, ...]:
    return (
        f'No file navigate can read under {target}.',
        reads_line(),
        'Next step: map a directory or a file with one of those suffixes.',
    )
