"""Scenarios for the board's per-section cap."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tests.params import as_params

if TYPE_CHECKING:
    import pytest
    from _pytest.mark import ParameterSet
    from red_thread_casefile.policy import CitationState


@dataclass(slots=True, kw_only=True, frozen=True)
class CapCase:
    name: str
    total: int
    shown_seqs: tuple[int, ...]
    hidden: int
    marks: tuple[pytest.MarkDecorator, ...] = ()


def section_cap_params() -> list[ParameterSet]:
    cases = [
        CapCase(name='under-the-cap', total=5, shown_seqs=(1, 2, 3, 4, 5), hidden=0),
        CapCase(name='at-the-cap', total=6, shown_seqs=(1, 2, 3, 4, 5, 6), hidden=0),
        CapCase(name='one-over-the-cap', total=7, shown_seqs=(2, 3, 4, 5, 6, 7), hidden=1),
        CapCase(name='two-over-the-cap', total=8, shown_seqs=(3, 4, 5, 6, 7, 8), hidden=2),
    ]
    return as_params(cases)


@dataclass(slots=True, kw_only=True, frozen=True)
class LeadCase:
    name: str
    finding_head: str | None
    board_head: str | None
    is_lead: bool
    recorded: str | None = None
    marks: tuple[pytest.MarkDecorator, ...] = ()


def lead_marker_params() -> list[ParameterSet]:
    cases = [
        LeadCase(
            name='same-head', finding_head='1111111aaaa', board_head='1111111aaaa', is_lead=False
        ),
        LeadCase(
            name='different-head',
            finding_head='1111111aaaa',
            board_head='2222222bbbb',
            is_lead=True,
            recorded='1111111',
        ),
        LeadCase(
            name='finding-had-no-commit',
            finding_head=None,
            board_head='2222222bbbb',
            is_lead=True,
            recorded='no commit',
        ),
        LeadCase(
            name='tree-has-no-commit-now',
            finding_head='1111111aaaa',
            board_head=None,
            is_lead=True,
            recorded='1111111',
        ),
        LeadCase(name='no-commit-then-or-now', finding_head=None, board_head=None, is_lead=False),
    ]
    return as_params(cases)


@dataclass(slots=True, kw_only=True, frozen=True)
class StateCount:
    name: str
    states: tuple[CitationState, ...]
    written: str
    marks: tuple[pytest.MarkDecorator, ...] = ()


def state_count_params() -> list[ParameterSet]:
    cases = [
        StateCount(name='no-citation-checked', states=(), written='none'),
        StateCount(name='one-ok', states=('ok',), written='1 ok'),
        StateCount(name='counts-repeat-states', states=('ok', 'ok', 'ok'), written='3 ok'),
        StateCount(
            name='states-keep-their-fixed-order',
            states=('unchecked', 'missing', 'changed', 'moved', 'ok'),
            written='1 ok, 1 moved, 1 changed, 1 missing, 1 unchecked',
        ),
        StateCount(
            name='order-does-not-follow-the-findings',
            states=('missing', 'ok', 'missing', 'ok', 'ok'),
            written='3 ok, 2 missing',
        ),
        StateCount(name='a-state-with-none-is-left-out', states=('changed',), written='1 changed'),
    ]
    return as_params(cases)
