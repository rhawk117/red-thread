"""Properties of the finding rules: a finding that breaks one is always a fault."""

from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.domain import FINDING_KINDS
from red_thread_casefile.errors import (
    DecisionInThreadError,
    DecisionSourceError,
    MissingRefuteError,
    OwnerInThreadError,
    UncitedKnownError,
    UncitedRuledOutError,
    UpgradedVerdictError,
)

from tests.casefile.ledger.builders import (
    URL_CITE,
    create_finding,
    create_framed_harness,
    create_valid_finding,
)

if TYPE_CHECKING:
    from red_thread_casefile.domain import CaseFinding, FindingKind
    from red_thread_casefile.errors import CaseFileError


def is_not_owner(source: str) -> bool:
    return source != 'user'


def make_thread_name(number: int) -> str:
    return f'T{number}'


def make_owner_finding(kind: FindingKind) -> CaseFinding:
    return create_valid_finding(kind).replace_with(source='user')


def make_decision_from(source: str) -> CaseFinding:
    return create_valid_finding('decision').replace_with(source=source)


def make_uncited_ruled_out(source: str) -> CaseFinding:
    return create_valid_finding('ruled_out').replace_with(citation=None, source=source)


class TestRuleProperties:
    thread_names = st.integers(min_value=1, max_value=99).map(make_thread_name)
    texts = st.text(min_size=1).filter(str.strip)
    uncited_known = st.builds(
        create_finding,
        kind=st.just('known'),
        text=texts,
        source=texts,
        verdict=st.sampled_from((None, 'VERIFIED')),
        citation=st.none(),
        quote=st.none() | texts,
        rests_on=st.none() | texts,
        refuted_if=st.none() | texts,
    )
    upgraded_known = st.builds(
        create_finding,
        kind=st.just('known'),
        text=texts,
        source=texts,
        verdict=st.sampled_from(('INFERRED', 'NEEDS-ANALYSIS', 'BLOCKED')),
        citation=st.just(URL_CITE),
        rests_on=st.none() | texts,
    )
    owner_findings = st.sampled_from(FINDING_KINDS).map(make_owner_finding)
    other_sources = texts.filter(is_not_owner)
    decisions_from_others = other_sources.map(make_decision_from)
    uncited_ruled_out = other_sources.map(make_uncited_ruled_out)
    unrefuted_hypotheses = st.builds(
        create_finding,
        kind=st.just('hypothesis'),
        text=texts,
        source=texts,
        refuted_if=st.none(),
    )

    def find_fault_kinds(
        self, finding: CaseFinding, thread: str | None = None
    ) -> set[type[CaseFileError]]:
        harness = create_framed_harness()
        harness.seed(thread, finding)
        return {type(problem) for problem in harness.find_problems()}

    @given(finding=uncited_known)
    def test_known_without_a_citation_is_always_a_fault(self, finding: CaseFinding) -> None:
        assert UncitedKnownError in self.find_fault_kinds(finding)

    @given(finding=upgraded_known)
    def test_known_with_a_weaker_verdict_is_always_a_fault(self, finding: CaseFinding) -> None:
        assert UpgradedVerdictError in self.find_fault_kinds(finding)

    @given(finding=owner_findings, thread=thread_names)
    def test_owner_finding_in_a_thread_is_always_a_fault(
        self, finding: CaseFinding, thread: str
    ) -> None:
        found = self.find_fault_kinds(finding, thread)

        assert found & {OwnerInThreadError, DecisionInThreadError}

    @given(finding=decisions_from_others)
    def test_decision_from_anyone_but_the_owner_is_always_a_fault(
        self, finding: CaseFinding
    ) -> None:
        assert DecisionSourceError in self.find_fault_kinds(finding)

    @given(finding=unrefuted_hypotheses)
    def test_hypothesis_without_refute_is_always_a_fault(self, finding: CaseFinding) -> None:
        assert MissingRefuteError in self.find_fault_kinds(finding)

    @given(finding=uncited_ruled_out)
    def test_ruled_out_without_citation_or_owner_is_always_a_fault(
        self, finding: CaseFinding
    ) -> None:
        assert UncitedRuledOutError in self.find_fault_kinds(finding)
