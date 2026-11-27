"""Frontmatter between --- fences: split a file's lines around the fences."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from red_thread_core.dto import DTO

if TYPE_CHECKING:
    from collections.abc import Sequence

FENCE = '---'

type FenceProblem = Literal['no_opening', 'no_closing']


@dataclass(slots=True, kw_only=True, frozen=True)
class FenceReasons:
    no_opening: str
    no_closing: str

    def explain(self, problem: FenceProblem) -> str:
        return self.no_opening if problem == 'no_opening' else self.no_closing


class FrontSplit(DTO, frozen=True, kw_only=True, gc=False):
    front: tuple[str, ...]
    closing: int


def find_closing(lines: Sequence[str]) -> int | None:
    found = (index for index, line in enumerate(lines) if index and line.strip() == FENCE)
    return next(found, None)


def split_frontmatter(lines: Sequence[str]) -> FrontSplit | FenceProblem:
    if not lines or lines[0].strip() != FENCE:
        return 'no_opening'

    closing = find_closing(lines)
    if closing is None:
        return 'no_closing'

    return FrontSplit(front=tuple(lines[1:closing]), closing=closing)
