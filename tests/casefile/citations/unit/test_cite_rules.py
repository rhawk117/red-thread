"""Check holds a cite written in the current round to its line, and names the one that misses."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.errors import MissingQuoteError, UnresolvedCitationError

from tests.casefile.citations.cases import (
    SLEEP_CITE,
    SLEEP_LINE,
    citation_rule_params,
    unread_citation_params,
)
from tests.casefile.ledger.builders import create_valid_finding
from tests.casefile.ledger.memory import NEXT_HEAD

if TYPE_CHECKING:
    from red_thread_casefile.domain import CaseFinding
    from red_thread_casefile.errors import CaseFileError

    from tests.casefile.citations.cases import CitationRuleCase
    from tests.casefile.ledger.builders import CaseHarness


def citation_rule_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', citation_rule_params())


def unread_citation_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('citation', unread_citation_params())


def create_cited(citation: str, quote: str | None, finding_number: int = 1) -> CaseFinding:
    return create_valid_finding('known', finding_number).replace_with(
        citation=citation, quote=quote
    )


class TestCitationRules:
    @pytest.fixture
    def harness(self, framed_harness: CaseHarness) -> CaseHarness:
        return framed_harness

    def find_problem(self, harness: CaseHarness) -> CaseFileError | None:
        problems = harness.find_problems()
        assert len(problems) <= 1
        return next(iter(problems), None)

    @citation_rule_cases()
    def test_a_fresh_citation_must_resolve_and_carry_a_quote_on_its_line(
        self, harness: CaseHarness, case: CitationRuleCase
    ) -> None:
        harness.seed(None, create_cited(case.citation, case.quote))

        problem = self.find_problem(harness)

        assert type(problem) is case.error_type
        assert getattr(problem, 'found_at', None) == case.found_at

    def test_a_missing_quote_names_the_line_to_copy(self, harness: CaseHarness) -> None:
        harness.seed(None, create_cited(SLEEP_CITE, None))

        [problem] = harness.find_problems()

        assert isinstance(problem, MissingQuoteError)
        assert problem.line == SLEEP_LINE

    def test_a_broken_citation_is_a_fault_at_its_own_finding_only(
        self, harness: CaseHarness
    ) -> None:
        harness.seed(
            None,
            create_cited(SLEEP_CITE, SLEEP_LINE, 1),
            create_cited('src/gone.py:1', 'x', 2),
        )

        problem = self.find_problem(harness)

        assert isinstance(problem, UnresolvedCitationError)
        assert problem.location.finding_id == 'e2'

    def test_a_ruled_out_finding_is_held_to_its_citation_too(self, harness: CaseHarness) -> None:
        harness.seed(
            None,
            create_valid_finding('ruled_out').replace_with(citation='src/gone.py:1', quote='x'),
        )

        [problem] = harness.find_problems()

        assert isinstance(problem, UnresolvedCitationError)

    def test_a_citation_from_an_earlier_head_is_reported_not_faulted(
        self, harness: CaseHarness
    ) -> None:
        harness.seed(None, create_cited(SLEEP_CITE, 'import threading'))
        harness.tree.advance(NEXT_HEAD)

        checked = harness.check()

        assert checked.problems == ()
        assert [citation_check.state for citation_check in checked.citation_checks] == ['changed']

    @unread_citation_cases()
    def test_a_citation_outside_the_tree_or_not_a_path_is_never_read(
        self, harness: CaseHarness, citation: str
    ) -> None:
        harness.seed(None, create_cited(citation, 'anything'))

        harness.check()

        assert harness.tree.reads == []
