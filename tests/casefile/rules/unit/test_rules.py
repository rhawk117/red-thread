"""Every fault check finds in the entries of a case file, and where it names it."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.domain import ENTRY_KINDS
from red_thread_casefile.errors import (
    CaseNotFoundError,
    DecisionInThreadError,
    MissingRefuteError,
    StrayThreadFileError,
    UncitedKnownError,
)

from tests.casefile.ledger.builders import create_entry, create_valid_entry
from tests.casefile.ledger.markdown import name_file, write_thread_text
from tests.casefile.rules.cases import (
    authority_rule_params,
    combined_rule_params,
    kind_rule_params,
    status_rule_params,
    stray_thread_file_params,
)
from tests.casefile.rules.places import place_entry

if TYPE_CHECKING:
    from tests.casefile.ledger.builders import CaseHarness
    from tests.casefile.rules.cases import RuleCase


def status_rule_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', status_rule_params())


def authority_rule_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', authority_rule_params())


def kind_rule_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', kind_rule_params())


def combined_rule_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', combined_rule_params())


def stray_thread_file_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('name', stray_thread_file_params())


def place_in(harness: CaseHarness, thread: str | None, seq: int) -> str:
    return place_entry(harness.repository.files[name_file(thread)], thread, seq)


class TestCheckReportsEveryFault:
    @pytest.fixture
    def harness(self, framed_harness: CaseHarness) -> CaseHarness:
        framed_harness.seed(
            None,
            create_valid_entry('open', 1),
            create_valid_entry('known', 2).replace_with(cite=None),
            create_valid_entry('hypothesis', 3).replace_with(refute=None),
        )
        framed_harness.seed('T1', create_valid_entry('open', 1), create_valid_entry('decision', 2))
        return framed_harness

    def test_every_fault_is_named_with_its_file_line_and_ref(self, harness: CaseHarness) -> None:
        expected = (
            (UncitedKnownError, place_in(harness, None, 2)),
            (MissingRefuteError, place_in(harness, None, 3)),
            (DecisionInThreadError, place_in(harness, 'T1', 2)),
        )

        problems = harness.find_problems()

        assert [type(problem) for problem in problems] == [kind for kind, _ in expected]
        named = zip(map(str, problems), expected, strict=True)
        assert all(text.startswith(place) for text, (_, place) in named)

    def test_check_writes_no_file(self, harness: CaseHarness) -> None:
        before = dict(harness.repository.files)

        harness.check()

        assert harness.repository.files == before

    def test_valid_entry_of_every_kind_gives_no_fault(self, framed_harness: CaseHarness) -> None:
        entries = [create_valid_entry(kind, seq) for seq, kind in enumerate(ENTRY_KINDS, 1)]
        framed_harness.seed(None, *entries)

        assert framed_harness.find_problems() == ()
        assert [entry.text for entry in framed_harness.entries] == [e.text for e in entries]

    def test_missing_case_is_not_found(self, case_harness: CaseHarness) -> None:
        with pytest.raises(CaseNotFoundError):
            case_harness.check()

    @stray_thread_file_cases()
    def test_stray_thread_file_is_a_fault(self, framed_harness: CaseHarness, name: str) -> None:
        stray = f'threads/{name}.md'
        framed_harness.repository.write(stray, write_thread_text([create_entry()]))

        problems = framed_harness.find_problems()

        assert [p.file for p in problems if isinstance(p, StrayThreadFileError)] == [stray]


class TestEntryRules:
    @pytest.fixture
    def harness(self, framed_harness: CaseHarness) -> CaseHarness:
        return framed_harness

    def assert_rule_outcome(self, harness: CaseHarness, case: RuleCase) -> None:
        harness.seed(case.thread, case.entry)

        problems = harness.find_problems()

        assert tuple(map(type, problems)) == case.error_types
        place = place_in(harness, case.thread, case.entry.seq)
        assert all(str(problem).startswith(place) for problem in problems)

    @status_rule_cases()
    def test_status_is_never_upgraded(self, harness: CaseHarness, case: RuleCase) -> None:
        self.assert_rule_outcome(harness, case)

    @authority_rule_cases()
    def test_only_the_owner_decides_and_only_in_the_case_file(
        self, harness: CaseHarness, case: RuleCase
    ) -> None:
        self.assert_rule_outcome(harness, case)

    @kind_rule_cases()
    def test_hypotheses_and_ruled_out_entries_carry_their_proof(
        self, harness: CaseHarness, case: RuleCase
    ) -> None:
        self.assert_rule_outcome(harness, case)

    @combined_rule_cases()
    def test_every_rule_an_entry_breaks_is_reported(
        self, harness: CaseHarness, case: RuleCase
    ) -> None:
        self.assert_rule_outcome(harness, case)
