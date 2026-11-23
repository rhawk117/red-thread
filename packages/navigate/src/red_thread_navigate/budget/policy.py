"""Fitting output to a token budget by stepping down rungs and cutting at a line boundary."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_navigate.budget.errors import BudgetBelowMinimumError, NoRungsError

if TYPE_CHECKING:
    from collections.abc import Sequence

CHARS_PER_TOKEN_NUMERATOR = 2
CHARS_PER_TOKEN_DENOMINATOR = 7
MIN_BUDGET = 32
NOTES_SHARE = 3
ELLIPSIS = '...'


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


def printed_tokens(text: str) -> int:
    """Estimate tokens for text with the newline that printing it adds."""
    return estimate_tokens(f'{text}\n')


def cut_to_budget(text: str, budget: int) -> str:
    """Cut text to a trailing ellipsis so it, printed with its newline, fits the budget."""
    keep = len(text)
    fitted = text
    while printed_tokens(fitted) > budget and keep > 0:
        keep -= 1
        fitted = f'{text[:keep]}{ELLIPSIS}'
    return fitted


def fit_notes(notes: tuple[str, ...], *, budget: int) -> tuple[str, ...]:
    """Keep the notes that fit in a share of the budget, ending with a count of the rest."""
    share = budget // NOTES_SHARE
    if estimate_tokens('\n'.join(notes)) <= share:
        return notes
    kept: list[str] = []
    for note in notes:
        more = f'and {len(notes) - len(kept) - 1} more notes'
        if estimate_tokens('\n'.join([*kept, note, more])) > share:
            break
        kept.append(note)
    return (*kept, f'and {len(notes) - len(kept)} more notes')


def footer_for(*, kept: int, total: int) -> str:
    return f'showing {kept} of {total}, raise --budget'


def cut_rung(lines: tuple[str, ...], *, budget: int) -> Fitted:
    total = len(lines)
    kept: list[str] = []
    for line in lines:
        candidate = '\n'.join([*kept, line, footer_for(kept=len(kept) + 1, total=total)])
        if printed_tokens(candidate) > budget:
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
        if printed_tokens(text) <= budget:
            return Fitted(text=text, rung=index, kept=len(lines), total=len(lines), cut=False)

    last = len(rungs) - 1
    cut = cut_rung(rungs[last], budget=budget)
    return Fitted(text=cut.text, rung=last, kept=cut.kept, total=cut.total, cut=True)
