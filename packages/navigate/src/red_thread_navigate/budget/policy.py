"""Fitting output to a token budget by stepping down rungs and cutting at a line boundary."""

from dataclasses import dataclass, field
from itertools import takewhile
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from red_thread_core.dto import DTO

from red_thread_navigate.budget.errors import BudgetBelowMinimumError, NoRungsError

if TYPE_CHECKING:
    from collections.abc import Sequence

CHARS_PER_TOKEN_NUMERATOR = 2
CHARS_PER_TOKEN_DENOMINATOR = 7
MIN_BUDGET = 32
NOTES_SHARE = 3
ELLIPSIS = '...'


class Fitted(DTO, frozen=True, kw_only=True, gc=False):
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
    def fits(self, kept: Sequence[str]) -> bool: ...


@dataclass(slots=True, kw_only=True, frozen=True)
class PrefixGate:
    check: PrefixCheck
    seen: list[str] = field(default_factory=list)

    def admits(self, item: str) -> bool:
        self.seen.append(item)
        return self.check.fits(tuple(self.seen))


def keep_prefix(items: Sequence[str], check: PrefixCheck) -> tuple[str, ...]:
    return tuple(takewhile(PrefixGate(check=check).admits, items))


def more_notes(count: int) -> str:
    return f'and {count} more notes'


@dataclass(slots=True, kw_only=True, frozen=True)
class NotesCheck:
    total: int
    share: int

    def fits(self, kept: Sequence[str]) -> bool:
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

    def fits(self, kept: Sequence[str]) -> bool:
        footer = footer_for(kept=len(kept), total=self.total)
        return printed_tokens('\n'.join([*kept, footer])) <= self.budget


def cut_rung(lines: Sequence[str], *, budget: int) -> Fitted:
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
