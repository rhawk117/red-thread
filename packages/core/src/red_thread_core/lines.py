"""A text as numbered lines, cut into parts at the lines that start with a mark."""

from itertools import pairwise
from typing import TYPE_CHECKING

from red_thread_core.dto import DTO

if TYPE_CHECKING:
    from collections.abc import Sequence


class Line(DTO, frozen=True, kw_only=True, gc=False):
    number: int
    text: str

    @property
    def is_blank(self) -> bool:
        return not self.text.strip()

    @property
    def mark(self) -> str:
        return self.text.strip()


class Cut(DTO, frozen=True, kw_only=True, gc=False):
    head: Line
    body: tuple[Line, ...]


class Cuts(DTO, frozen=True, kw_only=True, gc=False):
    preamble: tuple[Line, ...]
    parts: tuple[Cut, ...]


def split_lines(text: str) -> list[str]:
    folded = text.replace('\r\n', '\n')
    return folded.removesuffix('\n').split('\n') if folded else []


def number_lines(lines: Sequence[str], start: int) -> tuple[Line, ...]:
    return tuple(Line(number=number, text=text) for number, text in enumerate(lines, start))


def cut_at(lines: tuple[Line, ...], mark: str) -> Cuts:
    starts = [index for index, line in enumerate(lines) if line.text.startswith(mark)]
    parts = tuple(
        Cut(head=lines[start], body=lines[start + 1 : end])
        for start, end in pairwise((*starts, len(lines)))
    )
    first = starts[0] if starts else len(lines)
    return Cuts(preamble=lines[:first], parts=parts)


def trim(lines: tuple[Line, ...]) -> tuple[Line, ...]:
    filled = [index for index, line in enumerate(lines) if not line.is_blank]
    if not filled:
        return ()
    return lines[filled[0] : filled[-1] + 1]
