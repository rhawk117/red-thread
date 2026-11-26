"""Owned globs, the paths they match and whole valid plans, for the plan check properties."""

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Literal

from hypothesis import strategies as st
from red_thread_plans.domain import (
    Accept,
    Acceptance,
    Mitigate,
    PlanDraft,
    Risk,
    TicketDraft,
    YouIntervene,
)

from tests.casefile.entries.strategies import words
from tests.casefile.ledger.builders import CASE_ID
from tests.plans.revisions.builders import ALIAS, RESTING_REFS, WORKTREES

type GlobMode = Literal['keep', 'star', 'any', 'tail', 'deep', 'skip', 'dir']
type HandlingKind = Literal['accept', 'mitigate', 'criterion', 'recut']

GLOB_MODES: tuple[GlobMode, ...] = ('keep', 'star', 'any', 'tail', 'deep', 'skip', 'dir')
HANDLING_KINDS: tuple[HandlingKind, ...] = ('accept', 'mitigate', 'criterion', 'recut')
DOT_NAMES = frozenset({'.', '..'})
MAX_PARTS = 4


def is_name(segment: str) -> bool:
    return segment not in DOT_NAMES


def join_parts(parts: list[str]) -> str:
    return '/'.join(parts)


def join_owned(parts: list[str], as_directory: bool) -> str:
    joined = '/'.join(parts)
    return f'{joined}/' if as_directory else joined


def matches_owned(path: str, owned: str) -> bool:
    pattern = f'{owned}**' if owned.endswith('/') else owned
    return PurePosixPath(path).full_match(pattern)


def glob_segment(segment: str, mode: GlobMode) -> tuple[str, ...]:
    shapes: dict[GlobMode, tuple[str, ...]] = {
        'keep': (segment,),
        'star': ('*',),
        'any': (f'?{segment[1:]}',),
        'tail': (f'{segment[0]}*',),
        'deep': ('**',),
        'skip': ('**', segment),
        'dir': (segment,),
    }
    return shapes[mode]


def glob_path(path: str, modes: list[GlobMode]) -> str:
    parts = path.split('/')
    globbed = [
        shape
        for part, mode in zip(parts, modes, strict=False)
        for shape in glob_segment(part, mode)
    ]
    if modes[len(parts) - 1] == 'dir' and len(parts) > 1:
        return join_owned(globbed[:-1], as_directory=True)
    return join_parts(globbed)


names = st.text(alphabet='ab.', min_size=1, max_size=3).filter(is_name)
paths = st.lists(names, min_size=1, max_size=MAX_PARTS).map(join_parts)
segment_globs = st.text(alphabet='ab.*?', min_size=1, max_size=3).filter(is_name)
owned_globs = st.builds(
    join_owned,
    st.lists(st.one_of(segment_globs, st.just('**')), min_size=1, max_size=MAX_PARTS),
    st.booleans(),
)
glob_modes = st.lists(st.sampled_from(GLOB_MODES), min_size=MAX_PARTS, max_size=MAX_PARTS)
worktree_tails = st.lists(
    st.sampled_from(('**', '*', '*.py', 'a?', 'src', 'x.md', 'docs/')), min_size=1, max_size=3
).map(join_parts)


@dataclass(slots=True, kw_only=True, frozen=True)
class TicketSeed:
    worktree: int
    title: str
    why: str
    picks: tuple[int, ...]
    tails: tuple[str, ...]
    sentences: tuple[Acceptance, ...]


@dataclass(slots=True, kw_only=True, frozen=True)
class RiskSeed:
    kind: HandlingKind
    pick: int
    text: str


def name_ticket(index: int) -> str:
    return f't{index}'


def pick_dependencies(seeds: list[TicketSeed], index: int) -> tuple[str, ...]:
    worktree = seeds[index].worktree
    earlier = [name_ticket(number) for number in range(index) if seeds[number].worktree == worktree]
    if not earlier:
        return ()
    return tuple(dict.fromkeys(earlier[pick % len(earlier)] for pick in seeds[index].picks))


def create_seeded_ticket(seeds: list[TicketSeed], index: int) -> TicketDraft:
    seed = seeds[index]
    worktree = WORKTREES[seed.worktree]
    return TicketDraft(
        id=name_ticket(index),
        title=seed.title,
        why=seed.why,
        worktree=worktree,
        acceptance=seed.sentences,
        owns=tuple(f'{worktree}/{tail}' for tail in seed.tails),
        depends_on=pick_dependencies(seeds, index),
    )


def create_seeded_risk(seed: RiskSeed, number: int, tickets: tuple[TicketDraft, ...]) -> Risk:
    ticket = tickets[seed.pick % len(tickets)]
    handlings = {
        'accept': Accept(),
        'mitigate': Mitigate(ticket=ticket.id),
        'criterion': Mitigate(ticket=ticket.id, criterion=ticket.acceptance[0].criterion),
        'recut': YouIntervene(recut=(ticket.id,)),
    }
    return Risk(
        id=f'R{number}',
        risk=seed.text,
        signal=seed.text,
        handling=handlings[seed.kind],
        tickets=(ticket.id,),
    )


def assemble_plan(
    seeds: list[TicketSeed], risk_seeds: list[RiskSeed], texts: list[str]
) -> PlanDraft:
    tickets = tuple(create_seeded_ticket(seeds, index) for index in range(len(seeds)))
    risks = tuple(
        create_seeded_risk(seed, number, tickets) for number, seed in enumerate(risk_seeds, 1)
    )
    return PlanDraft(
        intent=texts[0],
        approach=texts[-1],
        cases={ALIAS: CASE_ID},
        invariants=tuple(texts[1:]),
        non_goals=tuple(texts[:1]),
        tickets=tickets,
        risks=risks,
    )


sentences = st.builds(
    Acceptance,
    criterion=words,
    required_by=st.lists(st.sampled_from(RESTING_REFS), min_size=1, max_size=2, unique=True).map(
        tuple
    ),
)
ticket_seeds = st.builds(
    TicketSeed,
    worktree=st.integers(min_value=0, max_value=len(WORKTREES) - 1),
    title=words,
    why=words,
    picks=st.lists(st.integers(min_value=0, max_value=9), max_size=3).map(tuple),
    tails=st.lists(worktree_tails, min_size=1, max_size=3).map(tuple),
    sentences=st.lists(sentences, min_size=1, max_size=3).map(tuple),
)
risk_seeds = st.builds(
    RiskSeed,
    kind=st.sampled_from(HANDLING_KINDS),
    pick=st.integers(min_value=0, max_value=9),
    text=words,
)
valid_plans = st.builds(
    assemble_plan,
    st.lists(ticket_seeds, min_size=1, max_size=8),
    st.lists(risk_seeds, max_size=3),
    st.lists(words, min_size=1, max_size=3),
)
