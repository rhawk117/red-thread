"""Mapping a path: index it, rank files and symbols by references, fit the listing to a budget."""

from collections import Counter
from collections.abc import Callable
from typing import TYPE_CHECKING

from red_thread_navigate.budget import fit_notes, fit_to_budget
from red_thread_navigate.map.views import RankedFile, RankedSymbol, empty_lines, map_rungs
from red_thread_navigate.symbols.services import index_path
from red_thread_navigate.walk import PathMissingError

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_navigate.symbols.domain import FileSymbols

type SymbolKey = Callable[[RankedSymbol], tuple[int, int] | int]


def by_references(item: RankedSymbol) -> tuple[int, int]:
    return (-item.references, item.symbol.start_line)


def by_source(item: RankedSymbol) -> int:
    return item.symbol.start_line


def rank_file(file: FileSymbols, counts: Counter[str], *, key: SymbolKey) -> RankedFile:
    symbols = (
        RankedSymbol(symbol=symbol, references=counts[symbol.name]) for symbol in file.symbols
    )
    return RankedFile(file=file, symbols=tuple(sorted(symbols, key=key)))


def rank_files(files: tuple[FileSymbols, ...], *, key: SymbolKey) -> tuple[RankedFile, ...]:
    counts = Counter(reference.name for file in files for reference in file.references)
    ranked = (rank_file(file, counts, key=key) for file in files)
    return tuple(sorted(ranked, key=lambda item: (-item.references, str(item.file.path))))


def map_path(path: Path, *, budget: int) -> str:
    """List the files and symbols under a path, most-referenced first, inside the budget."""
    if not path.exists():
        raise PathMissingError(path=path)
    index = index_path(path)
    notes = fit_notes(index.notes, budget=budget)
    if not index.files:
        rung = (*notes, *empty_lines(str(path)))
        return fit_to_budget((rung,), budget=budget).text
    key = by_source if path.is_file() else by_references
    ranked = rank_files(index.files, key=key)
    rungs = tuple((*notes, *rung) for rung in map_rungs(ranked))
    return fit_to_budget(rungs, budget=budget).text
