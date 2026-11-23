"""Formatting helpers shared by the verb views."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from red_thread_navigate.symbols.domain import Symbol


def span(symbol: Symbol) -> str:
    if symbol.end_line == symbol.start_line:
        return f'L{symbol.start_line}'
    return f'L{symbol.start_line}-L{symbol.end_line}'


def plural(count: int, noun: str) -> str:
    return f'{count} {noun}' if count == 1 else f'{count} {noun}s'
