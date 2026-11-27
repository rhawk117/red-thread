"""Scenarios for a thread file whose round or finding headings cannot be read."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_casefile.errors import (
    FindingBeforeRoundError,
    MalformedFindingHeadingError,
    MalformedRoundError,
    MissingBlockError,
    RoundOrderError,
    StrayTextError,
)

from tests.params import as_params

if TYPE_CHECKING:
    import pytest
    from _pytest.mark import ParameterSet
    from red_thread_casefile.errors import CaseFileError

ROUND = '## Round 1 · 2026-11-21 · none\n\n'
BLOCK = '```yaml\nkind: open\ntext: a question\nsource: scout\n```\n'


def write_raw_finding(heading: str) -> str:
    return f'{heading}\n\n{BLOCK}'


@dataclass(slots=True, kw_only=True, frozen=True)
class LayoutCase:
    name: str
    text: str
    error_type: type[CaseFileError]
    place: str
    marks: tuple[pytest.MarkDecorator, ...] = ()


def round_heading_case(name: str, heading: str) -> LayoutCase:
    return LayoutCase(
        name=name,
        text=f'{heading}\n\n{write_raw_finding("### e1")}',
        error_type=MalformedRoundError,
        place='threads/T1.md:1:',
    )


def finding_heading_case(name: str, heading: str) -> LayoutCase:
    return LayoutCase(
        name=name,
        text=f'{ROUND}{write_raw_finding(heading)}',
        error_type=MalformedFindingHeadingError,
        place='threads/T1.md:3:',
    )


def round_order_case(name: str, first: str) -> LayoutCase:
    return LayoutCase(
        name=name,
        text=f'{first}\n\n{write_raw_finding("### e1")}{ROUND}{write_raw_finding("### e2")}',
        error_type=RoundOrderError,
        place='threads/T1.md:10:',
    )


def layout_params() -> list[ParameterSet]:
    cases = [
        round_heading_case('round-without-a-number', '## Round two · 2026-11-21 · none'),
        round_heading_case('round-without-a-day', '## Round 1 · none'),
        round_heading_case('round-on-an-impossible-day', '## Round 1 · 2026-02-30 · none'),
        round_heading_case('round-without-a-head', '## Round 1 · 2026-11-21'),
        round_heading_case('round-with-a-short-head', '## Round 1 · 2026-11-21 · abc12'),
        round_heading_case('round-with-an-uppercase-head', '## Round 1 · 2026-11-21 · ABC1234'),
        round_heading_case('round-with-another-word', '## Step 1 · 2026-11-21 · none'),
        round_order_case('round-heading-repeated', '## Round 1 · 2026-11-21 · none'),
        round_order_case('round-number-going-down', '## Round 2 · 2026-11-21 · none'),
        finding_heading_case('finding-numbered-zero', '### e0'),
        finding_heading_case('finding-with-a-capital', '### E1'),
        finding_heading_case('finding-named-in-words', '### finding 1'),
        LayoutCase(
            name='finding-before-any-round',
            text=write_raw_finding('### e1'),
            error_type=FindingBeforeRoundError,
            place='threads/T1.md:1:',
        ),
        LayoutCase(
            name='finding-without-a-block',
            text=f'{ROUND}### e1\n\nkind: open\n',
            error_type=MissingBlockError,
            place='threads/T1.md:3 T1.e1:',
        ),
        LayoutCase(
            name='notes-between-the-round-and-its-finding',
            text=f'{ROUND}some notes\n\n{write_raw_finding("### e1")}',
            error_type=StrayTextError,
            place='threads/T1.md:3:',
        ),
    ]
    return as_params(cases)
