"""Check holds a cite written in the current round to its line, and names the entry that misses."""

from typing import TYPE_CHECKING

import pytest
from msgspec.structs import replace
from red_thread_casefile.errors import MissingQuoteError, UnresolvedCiteError

from tests.casefile.citations.cases import (
    SLEEP_CITE,
    SLEEP_LINE,
    cite_rule_params,
    unread_cite_params,
)
from tests.casefile.ledger.builders import create_valid_entry
from tests.casefile.ledger.memory import NEXT_HEAD

if TYPE_CHECKING:
    from red_thread_casefile.domain import Entry
    from red_thread_casefile.errors import CaseFileError

    from tests.casefile.citations.cases import CiteRuleCase
    from tests.casefile.ledger.builders import CaseHarness


def cite_rule_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', cite_rule_params())


def unread_cite_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('cite', unread_cite_params())


def create_cited(cite: str, quote: str | None, seq: int = 1) -> Entry:
    return replace(create_valid_entry('known', seq), cite=cite, quote=quote)


class TestCiteRules:
    @pytest.fixture
    def harness(self, framed_harness: CaseHarness) -> CaseHarness:
        return framed_harness

    def find_problem(self, harness: CaseHarness) -> CaseFileError | None:
        problems = harness.find_problems()
        assert len(problems) <= 1
        return next(iter(problems), None)

    @cite_rule_cases()
    def test_a_fresh_cite_must_resolve_and_carry_a_quote_on_its_line(
        self, harness: CaseHarness, case: CiteRuleCase
    ) -> None:
        harness.seed(None, create_cited(case.cite, case.quote))

        problem = self.find_problem(harness)

        assert type(problem) is case.error_type
        assert getattr(problem, 'found_at', None) == case.found_at

    def test_a_missing_quote_names_the_line_to_copy(self, harness: CaseHarness) -> None:
        harness.seed(None, create_cited(SLEEP_CITE, None))

        [problem] = harness.find_problems()

        assert isinstance(problem, MissingQuoteError)
        assert problem.line == SLEEP_LINE

    def test_a_broken_cite_is_a_fault_at_its_own_entry_only(self, harness: CaseHarness) -> None:
        harness.seed(
            None,
            create_cited(SLEEP_CITE, SLEEP_LINE, 1),
            create_cited('src/gone.py:1', 'x', 2),
        )

        problem = self.find_problem(harness)

        assert isinstance(problem, UnresolvedCiteError)
        assert problem.spot.ref == 'e2'

    def test_a_ruled_out_entry_is_held_to_its_cite_too(self, harness: CaseHarness) -> None:
        harness.seed(
            None, replace(create_valid_entry('ruled_out'), cite='src/gone.py:1', quote='x')
        )

        [problem] = harness.find_problems()

        assert isinstance(problem, UnresolvedCiteError)

    def test_a_cite_from_an_earlier_head_is_reported_not_faulted(
        self, harness: CaseHarness
    ) -> None:
        harness.seed(None, create_cited(SLEEP_CITE, 'import threading'))
        harness.tree.advance(NEXT_HEAD)

        checked = harness.check()

        assert checked.problems == ()
        assert [finding.state for finding in checked.findings] == ['changed']

    @unread_cite_cases()
    def test_a_cite_outside_the_tree_or_not_a_path_is_never_read(
        self, harness: CaseHarness, cite: str
    ) -> None:
        harness.seed(None, create_cited(cite, 'anything'))

        harness.check()

        assert harness.tree.reads == []
