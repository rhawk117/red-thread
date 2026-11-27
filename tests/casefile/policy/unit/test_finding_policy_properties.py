"""FindingPolicy: each rule names the findings that break it, and a finding gets all its faults."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.domain import FindingLocation
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
from red_thread_casefile.policy import FindingPolicy

from tests.casefile.findings.strategies import optional, words
from tests.casefile.ledger.builders import create_finding
from tests.params import as_params

if TYPE_CHECKING:
    from red_thread_casefile.domain import CaseFinding

type Fields = st.SearchStrategy[Any]

LOCATION = FindingLocation(file='threads/T1.md', line=7, finding_id='T1.e3')
seqs = st.integers(min_value=1, max_value=50)
agents = st.sampled_from(('scout', 'primary'))
threads = st.sampled_from(('T1', 'T2', 'T10'))
any_thread = optional(threads)
plain_kinds = st.sampled_from(('open', 'resource', 'next'))
quiet_verdicts = st.sampled_from(('VERIFIED', 'BLOCKED', 'NEEDS-ANALYSIS'))


def create_findings(**fields: Fields) -> st.SearchStrategy[CaseFinding]:
    base: dict[str, Fields] = {
        'finding_number': seqs,
        'text': words,
        'source': agents,
        'thread': any_thread,
    }
    return st.builds(create_finding, **{**base, **fields})


@dataclass(slots=True, kw_only=True, frozen=True)
class Rule:
    name: str
    findings: st.SearchStrategy[CaseFinding]
    error_types: tuple[type[Exception], ...]
    marks: tuple[pytest.MarkDecorator, ...] = ()


def single_rule_cases() -> list[Rule]:
    return [
        Rule(
            name='known-with-a-weaker-verdict-is-an-upgrade',
            findings=create_findings(
                kind=st.just('known'),
                citation=words,
                rests_on=words,
                verdict=st.sampled_from(('INFERRED', 'NEEDS-ANALYSIS', 'BLOCKED')),
            ),
            error_types=(UpgradedVerdictError,),
        ),
        Rule(
            name='known-without-a-cite',
            findings=create_findings(kind=st.just('known'), verdict=optional(st.just('VERIFIED'))),
            error_types=(UncitedKnownError,),
        ),
        Rule(
            name='inferred-without-rests-on',
            findings=create_findings(kind=plain_kinds, verdict=st.just('INFERRED')),
            error_types=(MissingRestsOnError,),
        ),
        Rule(
            name='decision-in-a-thread',
            findings=create_findings(
                kind=st.just('decision'), source=st.sampled_from(('user', 'scout')), thread=threads
            ),
            error_types=(DecisionInThreadError,),
        ),
        Rule(
            name='decision-from-an-agent',
            findings=create_findings(kind=st.just('decision'), thread=st.none()),
            error_types=(DecisionSourceError,),
        ),
        Rule(
            name='owner-in-a-thread',
            findings=create_findings(kind=plain_kinds, source=st.just('user'), thread=threads),
            error_types=(OwnerInThreadError,),
        ),
        Rule(
            name='hypothesis-without-refute',
            findings=create_findings(kind=st.just('hypothesis')),
            error_types=(MissingRefuteError,),
        ),
        Rule(
            name='ruled-out-from-an-agent-without-a-cite',
            findings=create_findings(kind=st.just('ruled_out')),
            error_types=(UncitedRuledOutError,),
        ),
    ]


def combined_rule_cases() -> list[Rule]:
    return [
        Rule(
            name='claim-and-kind-rules-are-both-broken',
            findings=create_findings(kind=st.just('hypothesis'), verdict=st.just('INFERRED')),
            error_types=(MissingRestsOnError, MissingRefuteError),
        ),
        Rule(
            name='claim-and-authority-rules-are-both-broken',
            findings=create_findings(kind=st.just('known'), source=st.just('user'), thread=threads),
            error_types=(UncitedKnownError, OwnerInThreadError),
        ),
        Rule(
            name='authority-and-kind-rules-are-both-broken',
            findings=create_findings(
                kind=st.just('hypothesis'), source=st.just('user'), thread=threads
            ),
            error_types=(OwnerInThreadError, MissingRefuteError),
        ),
    ]


def clean_rule_cases() -> list[Rule]:
    return [
        Rule(
            name='agent-finding-that-breaks-no-rule',
            findings=st.one_of(
                create_findings(
                    kind=st.just('known'), citation=words, verdict=optional(st.just('VERIFIED'))
                ),
                create_findings(kind=plain_kinds, verdict=optional(quiet_verdicts)),
                create_findings(kind=plain_kinds, verdict=st.just('INFERRED'), rests_on=words),
                create_findings(kind=st.just('hypothesis'), refuted_if=words),
                create_findings(kind=st.just('ruled_out'), citation=words),
            ),
            error_types=(),
        ),
        Rule(
            name='owner-finding-in-the-case-file',
            findings=st.one_of(
                create_findings(kind=st.just('decision'), source=st.just('user'), thread=st.none()),
                create_findings(
                    kind=st.just('ruled_out'), source=st.just('user'), thread=st.none()
                ),
                create_findings(kind=plain_kinds, source=st.just('user'), thread=st.none()),
            ),
            error_types=(),
        ),
    ]


def finding_rule_cases() -> pytest.MarkDecorator:
    rules = (*single_rule_cases(), *combined_rule_cases(), *clean_rule_cases())
    return pytest.mark.parametrize('rule', as_params(rules))


class TestFindingPolicyProperties:
    @finding_rule_cases()
    @given(data=st.data())
    def test_an_finding_gets_a_fault_for_every_rule_it_breaks_and_no_other(
        self, rule: Rule, data: st.DataObject
    ) -> None:
        finding = data.draw(rule.findings)

        problems = FindingPolicy(finding=finding, location=LOCATION).get_finding_issues()

        assert tuple(map(type, problems)) == rule.error_types
        assert all(problem.location == LOCATION for problem in problems)
