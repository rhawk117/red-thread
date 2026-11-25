"""Reads a line back into the text it came from."""

from typing import TYPE_CHECKING

from red_thread_casefile.documents import Code, Link

if TYPE_CHECKING:
    from red_thread_casefile.documents import Inline, Line


def write_back(node: Inline) -> str:
    if isinstance(node, Code):
        return f'`{node.value}`'

    if isinstance(node, Link):
        return node.url

    return node.value


def join_line(line: Line) -> str:
    return ''.join(map(write_back, line))
