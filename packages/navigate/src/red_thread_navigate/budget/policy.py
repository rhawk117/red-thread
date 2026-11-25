"""Fitting output to a token budget by stepping down rungs and cutting at a line boundary."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

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
    scaled = len(text) * CHARS_PER_TOKEN_NUMERATOR
    return -(-scaled // CHARS_PER_TOKEN_DENOMINATOR)


def printed_tokens(text: str) -> int:
    return estimate_tokens(f'{text}\n')


def cut_to_budget(text: str, budget: int) -> str:
    keep = len(text)
    fitted = text
    while printed_tokens(fitted) > budget and keep > 0:
        keep -= 1
        fitted = f'{text[:keep]}{ELLIPSIS}'
    return fitted


@runtime_checkable
class PrefixCheck(Protocol):
    def fits(self, kept: tuple[str, ...]) -> bool: ...


def keep_prefix(items: tuple[str, ...], check: PrefixCheck) -> tuple[str, ...]:
    sizes = range(1, len(items) + 1)
    misfit = next((size for size in sizes if not check.fits(items[:size])), len(items) + 1)
    return items[: misfit - 1]


def more_notes(count: int) -> str:
    return f'and {count} more notes'


@dataclass(slots=True, kw_only=True, frozen=True)
class NotesCheck:
    total: int
    share: int

    def fits(self, kept: tuple[str, ...]) -> bool:
        more = more_notes(self.total - len(kept))
        return estimate_tokens('\n'.join([*kept, more])) <= self.share


def fit_notes(notes: tuple[str, ...], *, budget: int) -> tuple[str, ...]:
    share = budget // NOTES_SHARE
    if estimate_tokens('\n'.join(notes)) <= share:
        return notes
    kept = keep_prefix(notes, NotesCheck(total=len(notes), share=share))
    return (*kept, more_notes(len(notes) - len(kept)))


def footer_for(*, kept: int, total: int) -> str:
    return f'showing {kept} of {total}, raise --budget'


@dataclass(slots=True, kw_only=True, frozen=True)
class FooterCheck:
    total: int
    budget: int

    def fits(self, kept: tuple[str, ...]) -> bool:
        footer = footer_for(kept=len(kept), total=self.total)
        return printed_tokens('\n'.join([*kept, footer])) <= self.budget


def cut_rung(lines: tuple[str, ...], *, budget: int) -> Fitted:
    total = len(lines)
    kept = keep_prefix(lines, FooterCheck(total=total, budget=budget))
    text = '\n'.join([*kept, footer_for(kept=len(kept), total=total)])
    return Fitted(text=text, rung=-1, kept=len(kept), total=total, cut=True)


def fit_to_budget(rungs: Sequence[tuple[str, ...]], *, budget: int) -> Fitted:
    if budget < MIN_BUDGET:
        raise BudgetBelowMinimumError(budget=budget, minimum=MIN_BUDGET)
    if not rungs:
        raise NoRungsError

    whole = next(
        (
            Fitted(text=text, rung=index, kept=len(lines), total=len(lines), cut=False)
            for index, lines in enumerate(rungs)
            if printed_tokens(text := '\n'.join(lines)) <= budget
        ),
        None,
    )
    if whole:
        return whole

    last = len(rungs) - 1
    cut = cut_rung(rungs[last], budget=budget)
    return Fitted(text=cut.text, rung=last, kept=cut.kept, total=cut.total, cut=True)


def fit_text(rungs: Sequence[tuple[str, ...]], *, budget: int) -> str:
    return fit_to_budget(rungs, budget=budget).text
