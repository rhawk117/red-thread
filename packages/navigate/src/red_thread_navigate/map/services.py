"""Mapping a path: index it, rank files and symbols by references, fit the listing to a budget."""

from collections import Counter
from typing import TYPE_CHECKING

from red_thread_navigate.budget import MIN_BUDGET, estimate_tokens, fit_to_budget
from red_thread_navigate.map.views import RankedFile, RankedSymbol, empty_lines, map_rungs
from red_thread_navigate.symbols.services import index_path

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_navigate.symbols.domain import FileSymbols


def rank_file(file: FileSymbols, counts: Counter[str]) -> RankedFile:
    ranked = sorted(
        (RankedSymbol(symbol=symbol, references=counts[symbol.name]) for symbol in file.symbols),
        key=lambda item: (-item.references, item.symbol.start_line),
    )
    return RankedFile(file=file, symbols=tuple(ranked))


def rank_files(files: tuple[FileSymbols, ...]) -> tuple[RankedFile, ...]:
    counts = Counter(reference.name for file in files for reference in file.references)
    ranked = (rank_file(file, counts) for file in files)
    return tuple(sorted(ranked, key=lambda item: (-item.references, str(item.file.path))))


def map_path(path: Path, *, budget: int) -> str:
    """List the files and symbols under a path, most-referenced first, inside the budget."""
    index = index_path(path)
    notes = '\n'.join(index.notes)
    if not index.files:
        return '\n'.join((*index.notes, *empty_lines(str(path))))
    room = max(budget - estimate_tokens(notes), MIN_BUDGET) if notes else budget
    fitted = fit_to_budget(map_rungs(rank_files(index.files)), budget=room)
    return f'{notes}\n{fitted.text}' if notes else fitted.text
