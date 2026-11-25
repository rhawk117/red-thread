"""Formatting helpers shared by the verb views."""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import PurePosixPath

    from red_thread_navigate.symbols.domain import Symbol

LINE_BREAK = re.compile(r'\r\n|\r|\n')


def span(symbol: Symbol) -> str:
    if symbol.end_line == symbol.start_line:
        return f'L{symbol.start_line}'
    return f'L{symbol.start_line}-L{symbol.end_line}'


def plural(count: int, noun: str) -> str:
    return f'{count} {noun}' if count == 1 else f'{count} {noun}s'


def symbol_address(path: PurePosixPath, symbol: Symbol) -> str:
    return f'{path}#{symbol.qualified_name}'


def split_lines(text: str) -> tuple[str, ...]:
    lines = list(map(str, LINE_BREAK.split(text)))
    if lines and not lines[-1]:
        lines.pop()
    return tuple(lines)
