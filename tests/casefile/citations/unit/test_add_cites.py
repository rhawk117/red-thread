"""Citations are resolved against the tree when an entry is added."""

from contextlib import suppress
from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.errors import BatchRejectedError, MisquotedCiteError

from tests.casefile.citations.cases import (
    SLEEP_CITE,
    add_cite_params,
    unread_cite_params,
)
from tests.casefile.ledger.builders import create_valid_draft, reject_batch

if TYPE_CHECKING:
    from tests.casefile.citations.cases import AddCiteCase
    from tests.casefile.ledger.builders import CaseHarness


def add_cite_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', add_cite_params())


def unread_cite_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('cite', unread_cite_params())


class TestCiteResolvedWhenAdded:
    @pytest.fixture
    def harness(self, framed_harness: CaseHarness) -> CaseHarness:
        return framed_harness

    @add_cite_cases()
    def test_cite_must_resolve_and_a_quote_must_be_on_its_line(
        self, harness: CaseHarness, case: AddCiteCase
    ) -> None:
        draft = replace(create_valid_draft('known'), cite=case.cite, quote=case.quote)

        if case.error_type is not None:
            rejection = reject_batch(harness, draft)
            [problem] = rejection.problems
            assert type(problem) is case.error_type
            assert problem.cite == case.cite
            assert problem.position == 1
            if isinstance(problem, MisquotedCiteError):
                assert problem.found_at == case.found_at
            return

        added = harness.add(draft)

        assert [(entry.cite, entry.quote) for entry in added.entries] == [
            (case.cite, case.stored_quote)
        ]
        assert harness.entries == added.entries

    def test_unresolved_cite_rejects_the_whole_batch(self, harness: CaseHarness) -> None:
        sound = replace(create_valid_draft('known', 1), cite=SLEEP_CITE)
        broken = replace(create_valid_draft('known', 2), cite='src/gone.py:1')

        reject_batch(harness, sound, broken)

        assert harness.entries == ()

    def test_ruled_out_entry_cites_are_resolved_too(self, harness: CaseHarness) -> None:
        draft = replace(create_valid_draft('ruled_out'), cite='src/gone.py:1')

        reject_batch(harness, draft)

    @unread_cite_cases()
    def test_cite_outside_the_tree_or_not_a_path_is_never_read(
        self, harness: CaseHarness, cite: str
    ) -> None:
        draft = replace(create_valid_draft('known'), cite=cite)

        with suppress(BatchRejectedError):
            harness.add(draft)

        assert harness.tree.reads == []
