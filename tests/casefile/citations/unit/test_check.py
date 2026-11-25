"""The check reports which stored citations still hold, against a tree that changed."""

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from msgspec import structs
from red_thread_casefile.policy import Finding

from tests.casefile.citations.cases import (
    SLEEP_CITE,
    SLEEP_LINE,
    check_state_params,
    unchecked_cite_params,
)
from tests.casefile.ledger.builders import (
    QUEUE_PATH,
    create_draft,
    create_entry,
    create_valid_draft,
)
from tests.casefile.redaction.cases import LEAKED

if TYPE_CHECKING:
    from tests.casefile.citations.cases import CheckCase
    from tests.casefile.ledger.builders import CaseHarness

CONFIG_PATH = 'src/config.py'
LEAK_LINE = 'AWS_KEY = "AKIAIOSFODNN7EXAMPLE"'
LEAK_MARK = '[REDACTED:aws-key]'


def check_state_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', check_state_params())


def unchecked_cite_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('cite', unchecked_cite_params())


class TestCheck:
    cited = create_entry(seq=1, kind='known', cite=SLEEP_CITE, quote=SLEEP_LINE, verdict='VERIFIED')

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

        findings = harness.casefile.check()

        assert findings == (
            Finding(ref='e1', cite=SLEEP_CITE, state=case.state, moved_to=case.moved_to),
        )

    @unchecked_cite_cases()
    def test_citation_that_is_not_a_path_in_the_tree_is_unchecked_and_never_read(
        self, framed_harness: CaseHarness, cite: str
    ) -> None:
        framed_harness.seed(None, create_entry(seq=1, kind='known', cite=cite, quote='anything'))

        findings = framed_harness.casefile.check()

        assert findings == (Finding(ref='e1', cite=cite, state='unchecked'),)
        assert framed_harness.tree.reads == []

    def test_thread_entry_is_reported_under_its_thread_ref(self, harness: CaseHarness) -> None:
        harness.seed('T3', structs.replace(self.cited, thread='T3'))
        harness.tree.write(QUEUE_PATH, ('# top', *harness.tree.files[QUEUE_PATH]))

        states = {finding.ref: finding.state for finding in harness.casefile.check()}

        assert states == {'e1': 'moved', 'T3.e1': 'moved'}

    def test_only_live_entries_with_a_cite_are_checked(self, framed_harness: CaseHarness) -> None:
        framed_harness.seed(
            None,
            structs.replace(self.cited, seq=1),
            create_entry(seq=2, kind='known', cite='src/gone.py:1', quote='x'),
            create_entry(seq=3, supersedes=('e2',)),
            create_entry(seq=4),
        )

        refs = [finding.ref for finding in framed_harness.casefile.check()]

        assert refs == ['e1']

    def test_ledger_with_no_citations_has_no_findings(self, framed_harness: CaseHarness) -> None:
        framed_harness.seed(None, create_entry(seq=1))

        assert framed_harness.casefile.check() == ()


class TestCheckAfterRedaction:
    @pytest.fixture
    def leak_harness(self, framed_harness: CaseHarness) -> CaseHarness:
        framed_harness.tree.write(CONFIG_PATH, ('import os', LEAK_LINE, 'REGION = "eu"'))
        return framed_harness

    def test_entry_whose_stored_quote_was_redacted_still_checks_ok(
        self, leak_harness: CaseHarness
    ) -> None:
        draft = replace(create_valid_draft('known'), cite=f'{CONFIG_PATH}:2')
        added = leak_harness.add(draft)

        findings = leak_harness.casefile.check()

        [entry] = added.entries
        assert LEAKED not in (entry.quote or '')
        assert LEAK_MARK in (entry.quote or '')
        assert findings == (Finding(ref='e1', cite=f'{CONFIG_PATH}:2', state='ok'),)

    def test_redacted_quote_supplied_with_the_secret_still_checks_ok(
        self, leak_harness: CaseHarness
    ) -> None:
        draft = replace(create_valid_draft('known'), cite=f'{CONFIG_PATH}:2', quote=LEAKED)
        leak_harness.add(draft)

        [finding] = leak_harness.casefile.check()

        assert finding.state == 'ok'

    def test_redacted_quote_is_still_moved_when_its_line_moves(
        self, leak_harness: CaseHarness
    ) -> None:
        leak_harness.add(replace(create_valid_draft('known'), cite=f'{CONFIG_PATH}:2'))
        leak_harness.tree.write(CONFIG_PATH, ('# new', 'import os', LEAK_LINE))

        [finding] = leak_harness.casefile.check()

        assert (finding.state, finding.moved_to) == ('moved', 3)

    def test_redacted_quote_is_still_changed_when_its_line_changes(
        self, leak_harness: CaseHarness
    ) -> None:
        leak_harness.add(replace(create_valid_draft('known'), cite=f'{CONFIG_PATH}:2'))
        leak_harness.tree.write(CONFIG_PATH, ('import os', 'AWS_REGION = "eu"', 'REGION = "eu"'))

        [finding] = leak_harness.casefile.check()

        assert finding.state == 'changed'

    def test_entry_without_a_cite_never_reaches_the_tree(self, framed_harness: CaseHarness) -> None:
        framed_harness.add(create_draft())

        framed_harness.casefile.check()

        assert framed_harness.tree.reads == []
