"""Who may retire which entry, and what a retired entry is still checked for."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.errors import UnknownSupersededError

from tests.casefile.ledger.builders import create_entry, create_valid_entry
from tests.casefile.rules.supersede_cases import (
    allowed_supersede_params,
    refused_supersede_params,
)

if TYPE_CHECKING:
    from tests.casefile.ledger.builders import CaseHarness
    from tests.casefile.rules.supersede_cases import SupersedeCase


def allowed_supersede_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', allowed_supersede_params())


def refused_supersede_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', refused_supersede_params())


class TestSupersedes:
    @pytest.fixture
    def harness(self, framed_harness: CaseHarness) -> CaseHarness:
        framed_harness.seed(None, create_entry(seq=1), create_entry(seq=2))
        framed_harness.seed('T1', create_entry(seq=1), create_entry(seq=2))
        framed_harness.seed('T2', create_entry(seq=1))
        framed_harness.seed('T10', create_entry(seq=1))
        return framed_harness

    def retire(self, harness: CaseHarness, case: SupersedeCase) -> None:
        seq = len(harness.scribe.files[case.thread]) + 1
        harness.seed(case.thread, create_entry(seq=seq, supersedes=case.refs))

    @allowed_supersede_cases()
    def test_allowed_retirement_leaves_the_live_set(
        self, harness: CaseHarness, case: SupersedeCase
    ) -> None:
        self.retire(harness, case)

        ledger = harness.casefile.load().ledger

        assert harness.find_problems() == ()
        assert not set(case.refs) & {entry.ref for entry in ledger.live}
        assert set(case.refs) <= ledger.refs

    @refused_supersede_cases()
    def test_refused_retirement_is_a_fault(self, harness: CaseHarness, case: SupersedeCase) -> None:
        self.retire(harness, case)

        assert tuple(map(type, harness.find_problems())) == (case.error_type,)

    def test_retired_entry_skips_the_content_rules(self, framed_harness: CaseHarness) -> None:
        uncited = create_valid_entry('known', 1).replace_with(cite=None)
        framed_harness.seed(None, uncited, create_entry(seq=2, supersedes=('e1',)))

        assert framed_harness.find_problems() == ()
        assert len(framed_harness.entries) == 2

    def test_retired_entry_keeps_the_supersede_check(self, framed_harness: CaseHarness) -> None:
        framed_harness.seed(
            None,
            create_entry(seq=1, supersedes=('e9',)),
            create_entry(seq=2, supersedes=('e1',)),
        )

        assert tuple(map(type, framed_harness.find_problems())) == (UnknownSupersededError,)
