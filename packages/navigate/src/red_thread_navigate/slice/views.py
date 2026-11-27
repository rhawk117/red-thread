"""The rungs of a slice: whole code or an outline, then labels, with notes last."""

from pathlib import PurePosixPath
from textwrap import indent

from red_thread_core.dto import DTO

from red_thread_navigate.budget import fit_notes
from red_thread_navigate.symbols.domain import Symbol
from red_thread_navigate.util import rung, span, symbol_address


class Found(DTO, frozen=True, kw_only=True, gc=False):
    path: PurePosixPath
    symbol: Symbol
    children: tuple[Symbol, ...]
    lines: tuple[str, ...]
    whole: bool


def numbered(lines: tuple[str, ...], first: int) -> tuple[str, ...]:
    return tuple(f'{number}: {line}' for number, line in enumerate(lines, start=first))


def line_address(path: PurePosixPath, start: int, end: int) -> str:
    return f'{path}#L{start}-L{end}'


def label(found: Found) -> str:
    symbol = found.symbol
    parent = f'in {symbol.parent}' if symbol.parent is not None else 'at the top level'
    address = symbol_address(found.path, symbol)
    return f'{address}  {symbol.kind_label}  {span(symbol)}  {parent}'


def body_line(found: Found) -> str:
    address = line_address(found.path, found.symbol.start_line, found.symbol.end_line)
    return f'body: {address}'


def child_line(found: Found, child: Symbol) -> str:
    signature = child.signature.splitlines()[0] if child.signature else child.name
    return f'  {child.kind_label} {signature}  {span(child)}  {symbol_address(found.path, child)}'


def every_line(_line: str) -> bool:
    return True


def indented(text: str) -> tuple[str, ...]:
    return tuple(indent(text, '  ', every_line).splitlines())


def outline_lines(found: Found) -> tuple[str, ...]:
    symbol = found.symbol
    docstring = indented(symbol.docstring) if symbol.docstring is not None else ()
    children = tuple(child_line(found, child) for child in found.children)
    return (label(found), *indented(symbol.signature), *docstring, *children, body_line(found))


def full_lines(found: Found) -> tuple[str, ...]:
    if not found.whole:
        return outline_lines(found)
    return (label(found), *numbered(found.lines, found.symbol.start_line))


def label_lines(found: Found) -> tuple[str, ...]:
    return (label(found), body_line(found))


def symbol_rungs(
    founds: tuple[Found, ...], notes: tuple[str, ...], *, budget: int
) -> tuple[tuple[str, ...], ...]:
    heading = (f'{len(founds)} definitions match',) if len(founds) > 1 else ()
    tail = fit_notes(notes, budget=budget)
    builders = (full_lines, outline_lines, label_lines)
    return tuple(
        (*heading, *(line for found in founds for line in build(found)), *tail)
        for build in builders
    )


def line_rungs(
    path: PurePosixPath, *, start: int, lines: tuple[str, ...]
) -> tuple[tuple[str, ...], ...]:
    header = line_address(path, start, start + len(lines) - 1)
    return (rung(header, numbered(lines, start)),)
