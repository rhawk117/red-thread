"""EntryPolicy: each rule names the entries that break it, and an entry gets every fault it has."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.domain import Spot
from red_thread_casefile.errors import (
    DecisionInThreadError,
    DecisionSourceError,
    MissingRefuteError,
    MissingRestsOnError,
    OwnerInThreadError,
    UncitedKnownError,
    UncitedRuledOutError,
    UpgradedVerdictError,
)
from red_thread_casefile.policy import EntryPolicy

from tests.casefile.entries.strategies import optional, words
from tests.casefile.ledger.builders import create_entry
from tests.params import as_params

if TYPE_CHECKING:
    from red_thread_casefile.domain import Entry

type Fields = st.SearchStrategy[Any]

SPOT = Spot(file='threads/T1.md', line=7, ref='T1.e3')
seqs = st.integers(min_value=1, max_value=50)
agents = st.sampled_from(('scout', 'primary'))
threads = st.sampled_from(('T1', 'T2', 'T10'))
any_thread = optional(threads)
plain_kinds = st.sampled_from(('open', 'resource', 'next'))
quiet_verdicts = st.sampled_from(('VERIFIED', 'BLOCKED', 'NEEDS-ANALYSIS'))


def create_entries(**fields: Fields) -> st.SearchStrategy[Entry]:
    base: dict[str, Fields] = {'seq': seqs, 'text': words, 'source': agents, 'thread': any_thread}
    return st.builds(create_entry, **{**base, **fields})


@dataclass(slots=True, kw_only=True, frozen=True)
class Rule:
    name: str
    entries: st.SearchStrategy[Entry]
    error_types: tuple[type[Exception], ...]
    marks: tuple[pytest.MarkDecorator, ...] = ()


def single_rule_cases() -> list[Rule]:
    return [
        Rule(
            name='known-with-a-weaker-verdict-is-an-upgrade',
            entries=create_entries(
                kind=st.just('known'),
                cite=words,
                rests_on=words,
                verdict=st.sampled_from(('INFERRED', 'NEEDS-ANALYSIS', 'BLOCKED')),
            ),
            error_types=(UpgradedVerdictError,),
        ),
        Rule(
            name='known-without-a-cite',
            entries=create_entries(kind=st.just('known'), verdict=optional(st.just('VERIFIED'))),
            error_types=(UncitedKnownError,),
        ),
        Rule(
            name='inferred-without-rests-on',
            entries=create_entries(kind=plain_kinds, verdict=st.just('INFERRED')),
            error_types=(MissingRestsOnError,),
        ),
        Rule(
            name='decision-in-a-thread',
            entries=create_entries(
                kind=st.just('decision'), source=st.sampled_from(('user', 'scout')), thread=threads
            ),
            error_types=(DecisionInThreadError,),
        ),
        Rule(
            name='decision-from-an-agent',
            entries=create_entries(kind=st.just('decision'), thread=st.none()),
            error_types=(DecisionSourceError,),
        ),
        Rule(
            name='owner-in-a-thread',
            entries=create_entries(kind=plain_kinds, source=st.just('user'), thread=threads),
            error_types=(OwnerInThreadError,),
        ),
        Rule(
            name='hypothesis-without-refute',
            entries=create_entries(kind=st.just('hypothesis')),
            error_types=(MissingRefuteError,),
        ),
        Rule(
            name='ruled-out-from-an-agent-without-a-cite',
            entries=create_entries(kind=st.just('ruled_out')),
            error_types=(UncitedRuledOutError,),
        ),
    ]


def combined_rule_cases() -> list[Rule]:
    return [
        Rule(
            name='claim-and-kind-rules-are-both-broken',
            entries=create_entries(kind=st.just('hypothesis'), verdict=st.just('INFERRED')),
            error_types=(MissingRestsOnError, MissingRefuteError),
        ),
        Rule(
            name='claim-and-authority-rules-are-both-broken',
            entries=create_entries(kind=st.just('known'), source=st.just('user'), thread=threads),
            error_types=(UncitedKnownError, OwnerInThreadError),
        ),
        Rule(
            name='authority-and-kind-rules-are-both-broken',
            entries=create_entries(
                kind=st.just('hypothesis'), source=st.just('user'), thread=threads
            ),
            error_types=(OwnerInThreadError, MissingRefuteError),
        ),
    ]


def clean_rule_cases() -> list[Rule]:
    return [
        Rule(
            name='agent-entry-that-breaks-no-rule',
            entries=st.one_of(
                create_entries(
                    kind=st.just('known'), cite=words, verdict=optional(st.just('VERIFIED'))
                ),
                create_entries(kind=plain_kinds, verdict=optional(quiet_verdicts)),
                create_entries(kind=plain_kinds, verdict=st.just('INFERRED'), rests_on=words),
                create_entries(kind=st.just('hypothesis'), refute=words),
                create_entries(kind=st.just('ruled_out'), cite=words),
            ),
            error_types=(),
        ),
        Rule(
            name='owner-entry-in-the-case-file',
            entries=st.one_of(
                create_entries(kind=st.just('decision'), source=st.just('user'), thread=st.none()),
                create_entries(kind=st.just('ruled_out'), source=st.just('user'), thread=st.none()),
                create_entries(kind=plain_kinds, source=st.just('user'), thread=st.none()),
            ),
            error_types=(),
        ),
    ]


def entry_rule_cases() -> pytest.MarkDecorator:
    rules = (*single_rule_cases(), *combined_rule_cases(), *clean_rule_cases())
    return pytest.mark.parametrize('rule', as_params(rules))


class TestEntryPolicyProperties:
    @entry_rule_cases()
    @given(data=st.data())
    def test_an_entry_gets_a_fault_for_every_rule_it_breaks_and_no_other(
        self, rule: Rule, data: st.DataObject
    ) -> None:
        entry = data.draw(rule.entries)

        problems = EntryPolicy(entry=entry, spot=SPOT).get_entry_issues()

        assert tuple(map(type, problems)) == rule.error_types
        assert all(problem.spot == SPOT for problem in problems)
