"""The check reports which stored citations still hold, against a tree that changed."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.policy import CitationCheck

from tests.casefile.citations.cases import (
    SLEEP_CITE,
    SLEEP_LINE,
    check_state_params,
    unchecked_citation_params,
)
from tests.casefile.ledger.builders import QUEUE_PATH, create_finding

if TYPE_CHECKING:
    from tests.casefile.citations.cases import CheckCase
    from tests.casefile.ledger.builders import CaseHarness

CONFIG_PATH = 'src/config.py'
LEAK_LINE = 'AWS_KEY = "AKIAIOSFODNN7EXAMPLE"'
SCRUBBED_LINE = 'AWS_KEY = "[REDACTED:aws-access-key]"'
SCRUBBED_CITE = f'{CONFIG_PATH}:2'


def check_state_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', check_state_params())


def unchecked_citation_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('citation', unchecked_citation_params())


class TestCheck:
    cited = create_finding(
        finding_number=1, kind='known', citation=SLEEP_CITE, quote=SLEEP_LINE, verdict='VERIFIED'
    )

    @pytest.fixture
    def harness(self, framed_harness: CaseHarness) -> CaseHarness:
        framed_harness.seed(None, self.cited)
        return framed_harness

    @check_state_cases()
    def test_citation_is_reported_in_its_state(self, harness: CaseHarness, case: CheckCase) -> None:
        if case.after is None:
            harness.tree.remove(QUEUE_PATH)
        if case.after is not None:
            harness.tree.write(QUEUE_PATH, case.after)

        citation_checks = harness.check().citation_checks

        assert citation_checks == (
            CitationCheck(
                finding_id='e1', citation=SLEEP_CITE, state=case.state, moved_to=case.moved_to
            ),
        )

    @unchecked_citation_cases()
    def test_citation_that_is_not_a_path_in_the_tree_is_unchecked_and_never_read(
        self, framed_harness: CaseHarness, citation: str
    ) -> None:
        framed_harness.seed(
            None,
            create_finding(finding_number=1, kind='known', citation=citation, quote='anything'),
        )

        citation_checks = framed_harness.check().citation_checks

        assert citation_checks == (
            CitationCheck(finding_id='e1', citation=citation, state='unchecked'),
        )
        assert framed_harness.tree.reads == []

    def test_thread_finding_is_reported_under_its_thread_finding_id(
        self, harness: CaseHarness
    ) -> None:
        harness.seed('T3', self.cited.replace_with(thread='T3'))
        harness.tree.write(QUEUE_PATH, ('# top', *harness.tree.files[QUEUE_PATH]))

        states = {
            citation_check.finding_id: citation_check.state
            for citation_check in harness.check().citation_checks
        }

        assert states == {'e1': 'moved', 'T3.e1': 'moved'}

    def test_only_live_findings_with_a_citation_are_checked(
        self, framed_harness: CaseHarness
    ) -> None:
        framed_harness.seed(
            None,
            self.cited.replace_with(finding_number=1),
            create_finding(finding_number=2, kind='known', citation='src/gone.py:1', quote='x'),
            create_finding(finding_number=3, supersedes=('e2',)),
            create_finding(finding_number=4),
        )

        finding_ids = [
            citation_check.finding_id for citation_check in framed_harness.check().citation_checks
        ]

        assert finding_ids == ['e1']

    def test_ledger_with_no_citations_has_no_citation_checks(
        self, framed_harness: CaseHarness
    ) -> None:
        framed_harness.seed(None, create_finding(finding_number=1))

        assert framed_harness.check().citation_checks == ()


class TestCheckAfterRedaction:
    scrubbed = create_finding(
        finding_number=1, kind='known', citation=SCRUBBED_CITE, quote=SCRUBBED_LINE
    )

    @pytest.fixture
    def leak_harness(self, framed_harness: CaseHarness) -> CaseHarness:
        framed_harness.tree.write(CONFIG_PATH, ('import os', LEAK_LINE, 'REGION = "eu"'))
        framed_harness.seed(None, self.scrubbed)
        return framed_harness

    def test_a_quote_written_scrubbed_checks_ok_against_the_line_with_the_secret(
        self, leak_harness: CaseHarness
    ) -> None:
        checked = leak_harness.check()

        assert checked.problems == ()
        assert checked.citation_checks == (
            CitationCheck(finding_id='e1', citation=SCRUBBED_CITE, state='ok'),
        )

    def test_a_scrubbed_quote_is_still_moved_when_its_line_moves(
        self, leak_harness: CaseHarness
    ) -> None:
        leak_harness.tree.write(CONFIG_PATH, ('# new', 'import os', LEAK_LINE))

        [citation_check] = leak_harness.check().citation_checks

        assert (citation_check.state, citation_check.moved_to) == ('moved', 3)

    def test_a_scrubbed_quote_is_still_changed_when_its_line_changes(
        self, leak_harness: CaseHarness
    ) -> None:
        leak_harness.tree.write(CONFIG_PATH, ('import os', 'AWS_REGION = "eu"', 'REGION = "eu"'))

        [citation_check] = leak_harness.check().citation_checks

        assert citation_check.state == 'changed'

    def test_finding_without_a_citation_never_reaches_the_tree(
        self, framed_harness: CaseHarness
    ) -> None:
        framed_harness.seed(None, create_finding())

        framed_harness.check()

        assert framed_harness.tree.reads == []
