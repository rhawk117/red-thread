"""Finding a name: index a path, list its definitions and then its references inside a budget."""

from typing import TYPE_CHECKING

from red_thread_navigate.budget import fit_notes, fit_text
from red_thread_navigate.find.views import Definition, Occurrence, find_rungs, none_lines

if TYPE_CHECKING:
    from red_thread_navigate.symbols.domain import FileSymbols
    from red_thread_navigate.symbols.services import Index


def by_path(file: FileSymbols) -> str:
    return str(file.path)


def is_match(qualified_name: str, name: str) -> bool:
    return qualified_name == name or qualified_name.endswith(f'.{name}')


def definitions_of(files: tuple[FileSymbols, ...], name: str) -> tuple[Definition, ...]:
    return tuple(
        Definition(path=file.path, symbol=symbol)
        for file in sorted(files, key=by_path)
        for symbol in file.symbols
        if is_match(symbol.qualified_name, name)
    )


def references_to(files: tuple[FileSymbols, ...], name: str) -> tuple[Occurrence, ...]:
    last = name.rsplit('.', 1)[-1]
    return tuple(
        Occurrence(path=file.path, line=reference.line)
        for file in sorted(files, key=by_path)
        for reference in file.references
        if reference.name in {name, last}
    )


def find_name(index: Index, name: str, *, budget: int) -> str:
    definitions = definitions_of(index.files, name)
    references = references_to(index.files, name)
    rungs = (none_lines(name, str(index.path)),)
    if definitions or references:
        rungs = find_rungs(definitions, references)
    notes = fit_notes(index.notes, budget=budget)
    return fit_text(tuple((*notes, *rung) for rung in rungs), budget=budget)
