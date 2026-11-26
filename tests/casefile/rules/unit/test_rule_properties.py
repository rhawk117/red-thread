"""Properties of the entry rules: an entry that breaks one is always a fault."""

from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st
from msgspec.structs import replace
from red_thread_casefile.domain import ENTRY_KINDS
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
    create_entry,
    create_framed_harness,
    create_valid_entry,
)

if TYPE_CHECKING:
    from red_thread_casefile.domain import Entry, EntryKind
    from red_thread_casefile.errors import CaseFileError


def is_not_owner(source: str) -> bool:
    return source != 'user'


def make_thread_name(number: int) -> str:
    return f'T{number}'


def make_owner_entry(kind: EntryKind) -> Entry:
    return replace(create_valid_entry(kind), source='user')


def make_decision_from(source: str) -> Entry:
    return replace(create_valid_entry('decision'), source=source)


def make_uncited_ruled_out(source: str) -> Entry:
    return replace(create_valid_entry('ruled_out'), cite=None, source=source)


class TestRuleProperties:
    thread_names = st.integers(min_value=1, max_value=99).map(make_thread_name)
    texts = st.text(min_size=1).filter(str.strip)
    uncited_known = st.builds(
        create_entry,
        kind=st.just('known'),
        text=texts,
        source=texts,
        verdict=st.sampled_from((None, 'VERIFIED')),
        cite=st.none(),
        quote=st.none() | texts,
        rests_on=st.none() | texts,
        refute=st.none() | texts,
    )
    upgraded_known = st.builds(
        create_entry,
        kind=st.just('known'),
        text=texts,
        source=texts,
        verdict=st.sampled_from(('INFERRED', 'NEEDS-ANALYSIS', 'BLOCKED')),
        cite=st.just(URL_CITE),
        rests_on=st.none() | texts,
    )
    owner_entries = st.sampled_from(ENTRY_KINDS).map(make_owner_entry)
    other_sources = texts.filter(is_not_owner)
    decisions_from_others = other_sources.map(make_decision_from)
    uncited_ruled_out = other_sources.map(make_uncited_ruled_out)
    unrefuted_hypotheses = st.builds(
        create_entry,
        kind=st.just('hypothesis'),
        text=texts,
        source=texts,
        refute=st.none(),
    )

    def find_fault_kinds(self, entry: Entry, thread: str | None = None) -> set[type[CaseFileError]]:
        harness = create_framed_harness()
        harness.seed(thread, entry)
        return {type(problem) for problem in harness.find_problems()}

    @given(entry=uncited_known)
    def test_known_without_a_cite_is_always_a_fault(self, entry: Entry) -> None:
        assert UncitedKnownError in self.find_fault_kinds(entry)

    @given(entry=upgraded_known)
    def test_known_with_a_weaker_verdict_is_always_a_fault(self, entry: Entry) -> None:
        assert UpgradedVerdictError in self.find_fault_kinds(entry)

    @given(entry=owner_entries, thread=thread_names)
    def test_owner_entry_in_a_thread_is_always_a_fault(self, entry: Entry, thread: str) -> None:
        found = self.find_fault_kinds(entry, thread)

        assert found & {OwnerInThreadError, DecisionInThreadError}

    @given(entry=decisions_from_others)
    def test_decision_from_anyone_but_the_owner_is_always_a_fault(self, entry: Entry) -> None:
        assert DecisionSourceError in self.find_fault_kinds(entry)

    @given(entry=unrefuted_hypotheses)
    def test_hypothesis_without_refute_is_always_a_fault(self, entry: Entry) -> None:
        assert MissingRefuteError in self.find_fault_kinds(entry)

    @given(entry=uncited_ruled_out)
    def test_ruled_out_without_cite_or_owner_is_always_a_fault(self, entry: Entry) -> None:
        assert UncitedRuledOutError in self.find_fault_kinds(entry)
