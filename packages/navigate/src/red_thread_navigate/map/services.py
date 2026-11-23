"""Mapping a path: index it, rank files and symbols by references, fit the listing to a budget."""

from collections import Counter
from typing import TYPE_CHECKING

from red_thread_navigate.budget import fit_notes, fit_to_budget
from red_thread_navigate.map.views import RankedFile, RankedSymbol, empty_lines, map_rungs
from red_thread_navigate.symbols.services import index_path

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_navigate.symbols.domain import FileSymbols


def by_references(item: RankedSymbol) -> tuple[int, int]:
    return (-item.references, item.symbol.start_line)


def by_source(item: RankedSymbol) -> tuple[int, int]:
    return (0, item.symbol.start_line)


def rank_file(file: FileSymbols, counts: Counter[str], *, in_source_order: bool) -> RankedFile:
    key = by_source if in_source_order else by_references
    symbols = (
        RankedSymbol(symbol=symbol, references=counts[symbol.name]) for symbol in file.symbols
    )
    return RankedFile(file=file, symbols=tuple(sorted(symbols, key=key)))


def rank_files(
    files: tuple[FileSymbols, ...], *, in_source_order: bool = False
) -> tuple[RankedFile, ...]:
    counts = Counter(reference.name for file in files for reference in file.references)
    ranked = (rank_file(file, counts, in_source_order=in_source_order) for file in files)
    return tuple(sorted(ranked, key=lambda item: (-item.references, str(item.file.path))))


def map_path(path: Path, *, budget: int) -> str:
    """List the files and symbols under a path, most-referenced first, inside the budget."""
    index = index_path(path)
    notes = fit_notes(index.notes, budget=budget)
    if not index.files:
        rung = (*notes, *empty_lines(str(path)))
        return fit_to_budget((rung,), budget=budget).text
    ranked = rank_files(index.files, in_source_order=path.is_file())
    rungs = tuple((*notes, *rung) for rung in map_rungs(ranked))
    return fit_to_budget(rungs, budget=budget).text
