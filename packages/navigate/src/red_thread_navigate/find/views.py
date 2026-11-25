"""The rungs of a find: definitions then references, then per-file counts, then counts alone."""

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_navigate.util import plural, span, symbol_address

if TYPE_CHECKING:
    from pathlib import PurePosixPath

    from red_thread_navigate.symbols.domain import Symbol


@dataclass(slots=True, kw_only=True, frozen=True)
class Definition:
    path: PurePosixPath
    symbol: Symbol


@dataclass(slots=True, kw_only=True, frozen=True)
class Occurrence:
    path: PurePosixPath
    line: int


def definition_line(definition: Definition) -> str:
    symbol = definition.symbol
    address = symbol_address(definition.path, symbol)
    return f'  {address}  {symbol.kind_label}  {span(symbol)}'


def header_line(definitions: tuple[Definition, ...], references: tuple[Occurrence, ...]) -> str:
    return f'{plural(len(definitions), "definition")}  {plural(len(references), "reference")}'


def reference_line(occurrence: Occurrence) -> str:
    return f'  {occurrence.path}:{occurrence.line}'


def full_rung(
    definitions: tuple[Definition, ...], references: tuple[Occurrence, ...]
) -> tuple[str, ...]:
    return (
        header_line(definitions, references),
        *map(definition_line, definitions),
        *map(reference_line, references),
    )


def count_lines(references: tuple[Occurrence, ...]) -> tuple[str, ...]:
    counts = Counter(str(occurrence.path) for occurrence in references)
    return tuple(
        f'  {path}  {plural(count, "reference")}' for path, count in sorted(counts.items())
    )


def counted_rung(
    definitions: tuple[Definition, ...], references: tuple[Occurrence, ...]
) -> tuple[str, ...]:
    return (
        header_line(definitions, references),
        *map(definition_line, definitions),
        *count_lines(references),
    )


def find_rungs(
    definitions: tuple[Definition, ...], references: tuple[Occurrence, ...]
) -> tuple[tuple[str, ...], ...]:
    return (
        full_rung(definitions, references),
        counted_rung(definitions, references),
        (header_line(definitions, references), *count_lines(references)),
    )


def none_lines(name: str, target: str) -> tuple[str, ...]:
    return (
        f'no matches for {name} in {target}',
        f'Next step: map {target} to see the names there, or rg {name} {target} for text matches.',
    )
