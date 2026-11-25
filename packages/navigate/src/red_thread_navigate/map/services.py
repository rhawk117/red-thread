"""Mapping a path: index it, rank files and symbols by references, fit the listing to a budget."""

from collections import Counter
from collections.abc import Callable
from operator import attrgetter
from typing import TYPE_CHECKING

from red_thread_navigate.budget import fit_notes, fit_text
from red_thread_navigate.map.views import RankedFile, RankedSymbol, empty_lines, map_rungs

if TYPE_CHECKING:
    from red_thread_navigate.symbols.domain import Backends, FileSymbols
    from red_thread_navigate.symbols.services import Index

type SymbolKey = Callable[[RankedSymbol], tuple[int, int] | int]


def by_references(item: RankedSymbol) -> tuple[int, int]:
    return (-item.references, item.symbol.start_line)


def by_file_rank(item: RankedFile) -> tuple[int, str]:
    return (-item.references, str(item.file.path))


def rank_file(file: FileSymbols, counts: Counter[str], *, key: SymbolKey) -> RankedFile:
    symbols = (
        RankedSymbol(symbol=symbol, references=counts[symbol.name]) for symbol in file.symbols
    )
    return RankedFile(file=file, symbols=tuple(sorted(symbols, key=key)))


def rank_files(files: tuple[FileSymbols, ...], *, key: SymbolKey) -> tuple[RankedFile, ...]:
    counts = Counter(reference.name for file in files for reference in file.references)
    ranked = (rank_file(file, counts, key=key) for file in files)
    return tuple(sorted(ranked, key=by_file_rank))


def map_path(index: Index, backends: Backends, *, budget: int) -> str:
    notes = fit_notes(index.notes, budget=budget)
    if not index.files:
        rung = (*notes, *empty_lines(str(index.path), backends))
        return fit_text((rung,), budget=budget)
    key = attrgetter('symbol.start_line') if index.single_file else by_references
    ranked = rank_files(index.files, key=key)
    rungs = tuple((*notes, *rung) for rung in map_rungs(ranked))
    return fit_text(rungs, budget=budget)
