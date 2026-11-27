"""Who may retire which finding, and what a retired finding is still checked for."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.errors import UnknownSupersededError

from tests.casefile.ledger.builders import create_finding, create_valid_finding
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
        framed_harness.seed(
            None, create_finding(finding_number=1), create_finding(finding_number=2)
        )
        framed_harness.seed(
            'T1', create_finding(finding_number=1), create_finding(finding_number=2)
        )
        framed_harness.seed('T2', create_finding(finding_number=1))
        framed_harness.seed('T10', create_finding(finding_number=1))
        return framed_harness

    def retire(self, harness: CaseHarness, case: SupersedeCase) -> None:
        finding_number = len(harness.scribe.files[case.thread]) + 1
        harness.seed(
            case.thread, create_finding(finding_number=finding_number, supersedes=case.finding_ids)
        )

    @allowed_supersede_cases()
    def test_allowed_retirement_leaves_the_live_set(
        self, harness: CaseHarness, case: SupersedeCase
    ) -> None:
        self.retire(harness, case)

        ledger = harness.casefile.load().ledger

        assert harness.find_problems() == ()
        assert not set(case.finding_ids) & {finding.finding_id for finding in ledger.live}
        assert set(case.finding_ids) <= ledger.finding_ids

    @refused_supersede_cases()
    def test_refused_retirement_is_a_fault(self, harness: CaseHarness, case: SupersedeCase) -> None:
        self.retire(harness, case)

        assert tuple(map(type, harness.find_problems())) == (case.error_type,)

    def test_retired_finding_skips_the_content_rules(self, framed_harness: CaseHarness) -> None:
        uncited = create_valid_finding('known', 1).replace_with(citation=None)
        framed_harness.seed(None, uncited, create_finding(finding_number=2, supersedes=('e1',)))

        assert framed_harness.find_problems() == ()
        assert len(framed_harness.findings) == 2

    def test_retired_finding_keeps_the_supersede_check(self, framed_harness: CaseHarness) -> None:
        framed_harness.seed(
            None,
            create_finding(finding_number=1, supersedes=('e9',)),
            create_finding(finding_number=2, supersedes=('e1',)),
        )

        assert tuple(map(type, framed_harness.find_problems())) == (UnknownSupersededError,)
