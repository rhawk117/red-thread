"""DraftPolicy: each storage rule rejects its drafts with its own error, and the rules rank."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.domain import Draft
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
from red_thread_casefile.policy import DraftPolicy

from tests.casefile.entries.strategies import optional, words

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet

type Fields = st.SearchStrategy[Any]

positions = st.integers(min_value=1, max_value=50)
agents = st.sampled_from(('scout', 'primary'))
threads = st.sampled_from(('T1', 'T2', 'T10'))
plain_kinds = st.sampled_from(('open', 'resource', 'next'))
quiet_verdicts = st.sampled_from(('VERIFIED', 'BLOCKED', 'NEEDS-ANALYSIS'))
no_thread = st.none()


def create_drafts(**fields: Fields) -> st.SearchStrategy[Draft]:
    base: dict[str, Fields] = {'position': positions, 'text': words, 'source': agents}
    return st.builds(Draft, **{**base, **fields})


@dataclass(slots=True, kw_only=True, frozen=True)
class Rule:
    name: str
    drafts: st.SearchStrategy[Draft]
    threads: st.SearchStrategy[str | None]
    error: type[Exception] | None

    @property
    def param(self) -> ParameterSet:
        return pytest.param(self, id=self.name)


def draft_rule_cases() -> pytest.MarkDecorator:
    rules = [
        Rule(
            name='known-with-a-weaker-verdict-is-an-upgrade',
            drafts=create_drafts(
                kind=st.just('known'),
                cite=words,
                rests_on=words,
                verdict=st.sampled_from(('INFERRED', 'NEEDS-ANALYSIS', 'BLOCKED')),
            ),
            threads=optional(threads),
            error=UpgradedVerdictError,
        ),
        Rule(
            name='known-without-a-cite',
            drafts=create_drafts(kind=st.just('known'), verdict=optional(st.just('VERIFIED'))),
            threads=optional(threads),
            error=UncitedKnownError,
        ),
        Rule(
            name='inferred-without-rests-on',
            drafts=create_drafts(kind=plain_kinds, verdict=st.just('INFERRED')),
            threads=optional(threads),
            error=MissingRestsOnError,
        ),
        Rule(
            name='decision-in-a-thread',
            drafts=create_drafts(
                kind=st.just('decision'), source=st.sampled_from(('user', 'scout'))
            ),
            threads=threads,
            error=DecisionInThreadError,
        ),
        Rule(
            name='decision-from-an-agent',
            drafts=create_drafts(kind=st.just('decision')),
            threads=no_thread,
            error=DecisionSourceError,
        ),
        Rule(
            name='owner-in-a-thread',
            drafts=create_drafts(kind=plain_kinds, source=st.just('user')),
            threads=threads,
            error=OwnerInThreadError,
        ),
        Rule(
            name='hypothesis-without-refute',
            drafts=create_drafts(kind=st.just('hypothesis')),
            threads=optional(threads),
            error=MissingRefuteError,
        ),
        Rule(
            name='ruled-out-from-an-agent-without-a-cite',
            drafts=create_drafts(kind=st.just('ruled_out')),
            threads=optional(threads),
            error=UncitedRuledOutError,
        ),
        Rule(
            name='claim-rule-beats-kind-rule',
            drafts=create_drafts(kind=st.just('hypothesis'), verdict=st.just('INFERRED')),
            threads=optional(threads),
            error=MissingRestsOnError,
        ),
        Rule(
            name='claim-rule-beats-authority-rule',
            drafts=create_drafts(kind=st.just('known'), source=st.just('user')),
            threads=threads,
            error=UncitedKnownError,
        ),
        Rule(
            name='authority-rule-beats-kind-rule',
            drafts=create_drafts(kind=st.just('hypothesis'), source=st.just('user')),
            threads=threads,
            error=OwnerInThreadError,
        ),
        Rule(
            name='agent-draft-that-breaks-no-rule',
            drafts=st.one_of(
                create_drafts(
                    kind=st.just('known'), cite=words, verdict=optional(st.just('VERIFIED'))
                ),
                create_drafts(kind=plain_kinds, verdict=optional(quiet_verdicts)),
                create_drafts(kind=plain_kinds, verdict=st.just('INFERRED'), rests_on=words),
                create_drafts(kind=st.just('hypothesis'), refute=words),
                create_drafts(kind=st.just('ruled_out'), cite=words),
            ),
            threads=optional(threads),
            error=None,
        ),
        Rule(
            name='owner-draft-outside-a-thread',
            drafts=st.one_of(
                create_drafts(kind=st.just('decision'), source=st.just('user')),
                create_drafts(kind=st.just('ruled_out'), source=st.just('user')),
                create_drafts(kind=plain_kinds, source=st.just('user')),
            ),
            threads=no_thread,
            error=None,
        ),
    ]
    return pytest.mark.parametrize('rule', [rule.param for rule in rules])


class TestDraftPolicyProperties:
    @draft_rule_cases()
    @given(data=st.data())
    def test_a_draft_gets_the_verdict_of_the_rule_it_breaks_or_none(
        self, rule: Rule, data: st.DataObject
    ) -> None:
        draft = data.draw(rule.drafts)
        thread = data.draw(rule.threads)

        problem = DraftPolicy(draft=draft, thread=thread).get_storage_problem()

        if rule.error is None:
            assert not problem
            return

        assert type(problem) is rule.error
        assert problem.position == draft.position
