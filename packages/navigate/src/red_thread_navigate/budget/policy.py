"""Fitting output to a token budget by stepping down rungs and cutting at a line boundary."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_navigate.budget.errors import BudgetBelowMinimumError, NoRungsError

if TYPE_CHECKING:
    from collections.abc import Sequence

CHARS_PER_TOKEN_NUMERATOR = 2
CHARS_PER_TOKEN_DENOMINATOR = 7
MIN_BUDGET = 32


@dataclass(slots=True, kw_only=True, frozen=True)
class Fitted:
    text: str
    rung: int
    kept: int
    total: int
    cut: bool


def estimate_tokens(text: str) -> int:
    """Estimate tokens at 3.5 characters per token, rounded up."""
    scaled = len(text) * CHARS_PER_TOKEN_NUMERATOR
    return -(-scaled // CHARS_PER_TOKEN_DENOMINATOR)


def footer_for(*, kept: int, total: int) -> str:
    return f'showing {kept} of {total}, raise --budget'


def cut_rung(lines: tuple[str, ...], *, budget: int) -> Fitted:
    total = len(lines)
    kept: list[str] = []
    for line in lines:
        candidate = '\n'.join([*kept, line, footer_for(kept=len(kept) + 1, total=total)])
        if estimate_tokens(candidate) > budget:
            break
        kept.append(line)
    text = '\n'.join([*kept, footer_for(kept=len(kept), total=total)])
    return Fitted(text=text, rung=-1, kept=len(kept), total=total, cut=True)


def fit_to_budget(rungs: Sequence[tuple[str, ...]], *, budget: int) -> Fitted:
    """Return the first rung that fits whole, else the last rung cut with a footer."""
    if budget < MIN_BUDGET:
        raise BudgetBelowMinimumError(budget=budget, minimum=MIN_BUDGET)
    if not rungs:
        raise NoRungsError

    for index, lines in enumerate(rungs):
        text = '\n'.join(lines)
        if estimate_tokens(text) <= budget:
            return Fitted(text=text, rung=index, kept=len(lines), total=len(lines), cut=False)

    last = len(rungs) - 1
    cut = cut_rung(rungs[last], budget=budget)
    return Fitted(text=cut.text, rung=last, kept=cut.kept, total=cut.total, cut=True)
