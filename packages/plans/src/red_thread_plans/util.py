"""Pure helpers of the plan checks: where two owned globs meet, cycles and a lane's stack order."""

from functools import cache
from graphlib import CycleError, TopologicalSorter
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from red_thread_plans.domain import TicketDraft

type Parts = tuple[str, ...]

DEEP = '**'
STAR = '*'
ANY = '?'
FILLER = 'x'
DOT = '.'
NAMED = 3


def advance(dots: int, char: str) -> int:
    if char != DOT:
        return NAMED
    return min(dots + 1, NAMED)


def pick(left: str, right: str) -> str | None:
    if left == ANY:
        return FILLER if right == ANY else right
    if right in {ANY, left}:
        return left
    return None


def prepend[T: (str, Parts)](head: T, rest: T | None) -> T | None:
    if rest is None:
        return None
    return head + rest


@cache
def meet_names(left: str, right: str, dots: int = 0) -> str | None:
    if not left and not right:
        return '' if dots == NAMED else None

    if left[:1] == STAR:
        return meet_star(left, right, dots)

    if right[:1] == STAR:
        return meet_star(right, left, dots)

    if not left or not right:
        return None

    char = pick(left[0], right[0])
    if char is None:
        return None
    return prepend(char, meet_names(left[1:], right[1:], advance(dots, char)))


def meet_star(starred: str, other: str, dots: int) -> str | None:
    if other[:1] == STAR and dots != NAMED:
        named = prepend(FILLER, meet_names(starred, other, NAMED))
        if named is not None:
            return named

    if (skipped := meet_names(starred[1:], other, dots)) is not None:
        return skipped

    if not other:
        return None

    if other[0] == STAR:
        return meet_names(starred, other[1:], dots)

    char = FILLER if other[0] == ANY else other[0]
    return prepend(char, meet_names(starred, other[1:], advance(dots, char)))


def split_owned(owned: str) -> Parts:
    parts = PurePosixPath(owned).parts
    if owned.endswith('/'):
        parts = (*parts, DEEP)
    if parts[-1:] == (DEEP,):
        return (*parts[:-1], STAR, DEEP)
    return parts


@cache
def meet_paths(left: Parts, right: Parts) -> Parts | None:
    if not left and not right:
        return ()

    if left[:1] == (DEEP,):
        return meet_deep(left, right)

    if right[:1] == (DEEP,):
        return meet_deep(right, left)

    if not left or not right:
        return None

    name = meet_names(left[0], right[0])
    if name is None:
        return None
    return prepend((name,), meet_paths(left[1:], right[1:]))


def meet_deep(deep: Parts, other: Parts) -> Parts | None:
    if (skipped := meet_paths(deep[1:], other)) is not None:
        return skipped

    if not other:
        return None

    if other[0] == DEEP:
        return meet_paths(deep, other[1:])

    name = meet_names(other[0], STAR)
    if name is None:
        return None
    return prepend((name,), meet_paths(deep, other[1:]))


def find_shared_path(left: str, right: str) -> str | None:
    shared = meet_paths(split_owned(left), split_owned(right))
    if shared is None:
        return None
    return '/'.join(shared)


def find_cycle(graph: Mapping[str, Iterable[str]]) -> tuple[str, ...] | None:
    try:
        TopologicalSorter(graph).prepare()
    except CycleError as error:
        return tuple(map(str, reversed(error.args[1])))
    return None


def find_ready(tickets: Sequence[TicketDraft], placed: list[str]) -> TicketDraft | None:
    waiting = (ticket for ticket in tickets if ticket.id not in placed)
    return next((ticket for ticket in waiting if set(ticket.depends_on) <= set(placed)), None)


def order_stack(tickets: Sequence[TicketDraft]) -> tuple[str, ...]:
    placed: list[str] = []
    while (ready := find_ready(tickets, placed)) is not None:
        placed.append(ready.id)
    return tuple(placed)
