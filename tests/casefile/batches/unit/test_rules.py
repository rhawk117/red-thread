"""The rules a batch must satisfy before anything is stored, over memory fakes."""

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.domain import ENTRY_KINDS, VERDICTS, Draft
from red_thread_casefile.errors import (
    CaseNotFoundError,
    DecisionSourceError,
    InvalidFieldError,
    InvalidThreadError,
    UncitedKnownError,
)
from red_thread_casefile.schemas import parse_batch
from red_thread_casefile.services import Batch

from tests.casefile.batches.cases import (
    authority_rule_params,
    invalid_thread_params,
    kind_rule_params,
    status_rule_params,
)
from tests.casefile.batches.supersede_cases import supersede_params
from tests.casefile.ledger.builders import (
    URL_CITE,
    create_batch_text,
    create_draft,
    create_entry,
    create_framed_harness,
    create_valid_draft,
    reject_batch,
)

if TYPE_CHECKING:
    from red_thread_casefile.domain import EntryKind

    from tests.casefile.batches.cases import RuleCase
    from tests.casefile.batches.supersede_cases import SupersedeCase
    from tests.casefile.ledger.builders import CaseHarness


def is_not_owner(source: str) -> bool:
    return source != 'user'


def make_thread_name(number: int) -> str:
    return f'T{number}'


def make_owner_draft(kind: EntryKind) -> Draft:
    return replace(create_valid_draft(kind), source='user')


def make_decision_from(source: str) -> Draft:
    return replace(create_valid_draft('decision'), source=source)


def make_uncited_ruled_out(source: str) -> Draft:
    return replace(create_valid_draft('ruled_out'), cite=None, source=source)


def status_rule_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', status_rule_params())


def authority_rule_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', authority_rule_params())


def kind_rule_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', kind_rule_params())


def invalid_thread_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('thread', invalid_thread_params())


def supersede_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', supersede_params())


class TestBatchIsValidatedWhole:
    @pytest.fixture
    def harness(self, framed_harness: CaseHarness) -> CaseHarness:
        return framed_harness

    def test_one_bad_entry_stores_nothing(self, harness: CaseHarness) -> None:
        good = create_valid_draft('open', 1)
        bad = replace(create_valid_draft('known', 2), cite=None)
        also_good = create_valid_draft('hypothesis', 3)

        reject_batch(harness, good, bad, also_good)

        assert harness.entries == ()

    def test_error_lists_every_problem_shape_and_rule_together(self, harness: CaseHarness) -> None:
        text = create_batch_text(
            {'kind': 'known', 'text': 'the sleep blocks', 'source': 'scout'},
            {'kind': 'bogus', 'text': 'a made up kind', 'source': 'scout'},
            {'kind': 'decision', 'text': 'use a queue', 'source': 'scout'},
            {'kind': 'open', 'text': 'a fine entry', 'source': 'scout'},
        )
        parsed = parse_batch(text)

        rejection = reject_batch(harness, *parsed.drafts, problems=parsed.problems)

        listed = {(type(problem), problem.position) for problem in rejection.problems}
        assert listed == {
            (UncitedKnownError, 1),
            (InvalidFieldError, 2),
            (DecisionSourceError, 3),
        }
        message = str(rejection)
        assert all(f'entry {position}:' in message for position in (1, 2, 3))
        assert 'entry 4:' not in message
        assert harness.entries == ()

    def test_rejected_batch_leaves_the_next_seq_unused(self, harness: CaseHarness) -> None:
        reject_batch(harness, create_valid_draft('open', 1), create_draft(2, kind='known'))

        added = harness.add(create_valid_draft('open'))

        assert [entry.ref for entry in added.entries] == ['e1']

    def test_valid_batch_is_stored_whole_and_in_order(self, harness: CaseHarness) -> None:
        drafts = [
            create_valid_draft(kind, position) for position, kind in enumerate(ENTRY_KINDS, 1)
        ]

        added = harness.add(*drafts)

        assert [entry.text for entry in harness.entries] == [draft.text for draft in drafts]
        assert harness.entries == added.entries

    def test_missing_case_is_not_found_rather_than_a_rejected_batch(
        self, case_harness: CaseHarness
    ) -> None:
        with pytest.raises(CaseNotFoundError):
            case_harness.casefile.add(Batch(drafts=(create_draft(),), round=1))

    @invalid_thread_cases()
    def test_invalid_thread_name_is_refused_before_anything_is_stored(
        self, harness: CaseHarness, thread: str
    ) -> None:
        batch = Batch(drafts=(create_draft(),), round=1, thread=thread)

        with pytest.raises(InvalidThreadError) as raised:
            harness.casefile.add(batch)

        assert raised.value.thread == thread
        assert harness.entries == ()


class TestDraftRules:
    @pytest.fixture
    def harness(self, framed_harness: CaseHarness) -> CaseHarness:
        return framed_harness

    def assert_case_outcome(self, harness: CaseHarness, case: RuleCase) -> None:
        if case.error_type is None:
            added = harness.add(case.draft, thread=case.thread)
            assert harness.entries == added.entries
            assert len(added.entries) == 1
            return

        rejection = reject_batch(harness, case.draft, thread=case.thread)
        assert [type(problem) for problem in rejection.problems] == [case.error_type]

    @status_rule_cases()
    def test_status_is_never_upgraded(self, harness: CaseHarness, case: RuleCase) -> None:
        self.assert_case_outcome(harness, case)

    @authority_rule_cases()
    def test_only_the_owner_decides_and_only_in_the_ledger(
        self, harness: CaseHarness, case: RuleCase
    ) -> None:
        self.assert_case_outcome(harness, case)

    @kind_rule_cases()
    def test_hypotheses_and_ruled_out_entries_carry_their_proof(
        self, harness: CaseHarness, case: RuleCase
    ) -> None:
        self.assert_case_outcome(harness, case)


class TestStorabilityProperties:
    thread_names = st.integers(min_value=1, max_value=99).map(make_thread_name)
    sources = st.text(min_size=1)
    uncited_known = st.builds(
        Draft,
        position=st.just(1),
        kind=st.just('known'),
        text=st.text(min_size=1),
        source=sources,
        verdict=st.sampled_from((None, *VERDICTS)),
        cite=st.none(),
        quote=st.none() | st.text(min_size=1),
        rests_on=st.none() | st.text(min_size=1),
        refute=st.none() | st.text(min_size=1),
    )
    upgraded_known = st.builds(
        Draft,
        position=st.just(1),
        kind=st.just('known'),
        text=st.text(min_size=1),
        source=sources,
        verdict=st.sampled_from(('INFERRED', 'NEEDS-ANALYSIS', 'BLOCKED')),
        cite=st.just(URL_CITE),
        rests_on=st.none() | st.text(min_size=1),
    )
    owner_drafts = st.sampled_from(ENTRY_KINDS).map(make_owner_draft)
    non_owner_sources = sources.filter(is_not_owner)
    decisions_from_others = non_owner_sources.map(make_decision_from)
    uncited_ruled_out = non_owner_sources.map(make_uncited_ruled_out)
    unrefuted_hypotheses = st.builds(
        Draft,
        position=st.just(1),
        kind=st.just('hypothesis'),
        text=st.text(min_size=1),
        source=sources,
        refute=st.none(),
    )

    def assert_never_stored(self, draft: Draft, thread: str | None = None) -> None:
        harness = create_framed_harness()

        reject_batch(harness, draft, thread=thread)

        assert harness.entries == ()

    @given(draft=uncited_known)
    def test_known_without_a_cite_is_never_storable(self, draft: Draft) -> None:
        self.assert_never_stored(draft)

    @given(draft=upgraded_known)
    def test_known_with_a_weaker_verdict_is_never_storable(self, draft: Draft) -> None:
        self.assert_never_stored(draft)

    @given(draft=owner_drafts, thread=thread_names)
    def test_thread_never_stores_an_entry_from_the_owner(self, draft: Draft, thread: str) -> None:
        self.assert_never_stored(draft, thread)

    @given(draft=decisions_from_others)
    def test_decision_from_anyone_but_the_owner_is_never_storable(self, draft: Draft) -> None:
        self.assert_never_stored(draft)

    @given(draft=unrefuted_hypotheses)
    def test_hypothesis_without_refute_is_never_storable(self, draft: Draft) -> None:
        self.assert_never_stored(draft)

    @given(draft=uncited_ruled_out)
    def test_ruled_out_without_cite_or_owner_is_never_storable(self, draft: Draft) -> None:
        self.assert_never_stored(draft)


class TestSupersedes:
    @pytest.fixture
    def harness(self, framed_harness: CaseHarness) -> CaseHarness:
        framed_harness.seed(None, create_entry(seq=1), create_entry(seq=2))
        framed_harness.seed('T1', create_entry(seq=1), create_entry(seq=2))
        framed_harness.seed('T2', create_entry(seq=1))
        framed_harness.seed('T10', create_entry(seq=1))
        return framed_harness

    @supersede_cases()
    def test_retirement_follows_who_may_retire_what(
        self, harness: CaseHarness, case: SupersedeCase
    ) -> None:
        draft = replace(create_draft(), supersedes=case.refs)
        refs_before = harness.repository.read_ledger().refs

        if case.error_type is not None:
            rejection = reject_batch(harness, draft, thread=case.thread)
            assert [type(problem) for problem in rejection.problems] == [case.error_type]
            assert harness.repository.read_ledger().live == harness.entries
            return

        added = harness.add(draft, thread=case.thread)
        ledger = harness.repository.read_ledger()
        assert ledger.refs == refs_before | {entry.ref for entry in added.entries}
        assert not set(case.refs) & {entry.ref for entry in ledger.live}
        assert set(case.refs) <= ledger.refs

    def test_retired_entry_is_not_edited(self, harness: CaseHarness) -> None:
        before = harness.entries

        harness.add(replace(create_draft(), supersedes=('e1',)))

        assert set(before) <= set(harness.entries)
