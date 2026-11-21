"""Scenarios for the board's per-section cap."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet


@dataclass(slots=True, kw_only=True, frozen=True)
class CapCase:
    name: str
    total: int
    shown_seqs: tuple[int, ...]
    hidden: int

    @property
    def param(self) -> ParameterSet:
        return pytest.param(self, id=self.name)


def section_cap_params() -> list[ParameterSet]:
    cases = [
        CapCase(name='under-the-cap', total=5, shown_seqs=(1, 2, 3, 4, 5), hidden=0),
        CapCase(name='at-the-cap', total=6, shown_seqs=(1, 2, 3, 4, 5, 6), hidden=0),
        CapCase(name='one-over-the-cap', total=7, shown_seqs=(2, 3, 4, 5, 6, 7), hidden=1),
        CapCase(name='two-over-the-cap', total=8, shown_seqs=(3, 4, 5, 6, 7, 8), hidden=2),
    ]
    return [case.param for case in cases]


@dataclass(slots=True, kw_only=True, frozen=True)
class LeadCase:
    name: str
    entry_head: str | None
    board_head: str | None
    is_lead: bool
    recorded: str | None = None

    @property
    def param(self) -> ParameterSet:
        return pytest.param(self, id=self.name)


def lead_marker_params() -> list[ParameterSet]:
    cases = [
        LeadCase(
            name='same-head', entry_head='1111111aaaa', board_head='1111111aaaa', is_lead=False
        ),
        LeadCase(
            name='different-head',
            entry_head='1111111aaaa',
            board_head='2222222bbbb',
            is_lead=True,
            recorded='1111111',
        ),
        LeadCase(
            name='entry-had-no-commit',
            entry_head=None,
            board_head='2222222bbbb',
            is_lead=True,
            recorded='no commit',
        ),
        LeadCase(
            name='tree-has-no-commit-now',
            entry_head='1111111aaaa',
            board_head=None,
            is_lead=True,
            recorded='1111111',
        ),
        LeadCase(name='no-commit-then-or-now', entry_head=None, board_head=None, is_lead=False),
    ]
    return [case.param for case in cases]
