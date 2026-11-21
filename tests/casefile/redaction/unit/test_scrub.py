"""Secrets are replaced before storage, counted, and ordinary text is left alone."""

import string
from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.redaction import create_secret_patterns

from tests.casefile.ledger.builders import create_draft, create_valid_draft
from tests.casefile.redaction.cases import ordinary_text_params, secret_params

if TYPE_CHECKING:
    from collections.abc import Callable

    from red_thread_casefile.domain import Draft

    from tests.casefile.ledger.builders import CaseHarness
    from tests.casefile.redaction.cases import SecretCase

LEAKED = 'AKIAIOSFODNN7EXAMPLE'
LEAK_MARK = '[REDACTED:aws-key]'
LEAK_LINE = f'AWS_KEY = "{LEAKED}"'


def make_text_draft(text: str) -> Draft:
    return replace(create_draft(), text=text)


def make_cite_draft(text: str) -> Draft:
    return replace(create_valid_draft('known'), cite=f'curl -H "Authorization: Bearer {text}"')


def make_rests_on_draft(text: str) -> Draft:
    return replace(create_draft(), verdict='INFERRED', rests_on=f'a note with {text}')


def make_refute_draft(text: str) -> Draft:
    return replace(create_valid_draft('hypothesis'), refute=f'a log showing {text}')


def make_quote_draft(text: str) -> Draft:
    return replace(create_valid_draft('known'), cite='src/config.py:2', quote=text)


def make_diagram_draft(text: str) -> Draft:
    return replace(create_draft(), diagram=f'flowchart TD\n  A["{text}"] --> B\n  B --> C')


def secret_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', secret_params())


def ordinary_text_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('text', ordinary_text_params())


class TestScrub:
    patterns = create_secret_patterns()
    benign_text = st.text(alphabet=string.ascii_lowercase + string.digits + ' ', max_size=200)

    @secret_cases()
    def test_secret_is_replaced_and_counted_once(self, case: SecretCase) -> None:
        scrubbed = self.patterns.scrub(case.text)

        assert case.leaked not in scrubbed.text
        assert f'[REDACTED:{case.pattern}]' in scrubbed.text
        assert scrubbed.hits == 1

    @ordinary_text_cases()
    def test_ordinary_text_survives(self, text: str) -> None:
        scrubbed = self.patterns.scrub(text)

        assert scrubbed.text == text
        assert scrubbed.hits == 0

    @given(text=benign_text)
    def test_text_with_no_secret_shape_is_never_changed(self, text: str) -> None:
        scrubbed = self.patterns.scrub(text)

        assert scrubbed.text == text
        assert scrubbed.hits == 0

    def test_every_secret_in_a_text_is_counted(self) -> None:
        text = f'{LEAKED} then ghp_a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8 then {LEAKED}'

        scrubbed = self.patterns.scrub(text)

        assert scrubbed.hits == 3
        assert scrubbed.text.count('[REDACTED:') == 3


class TestRedactedBeforeStorage:
    @pytest.fixture
    def harness(self, framed_harness: CaseHarness) -> CaseHarness:
        framed_harness.tree.write('src/config.py', ('import os', LEAK_LINE))
        return framed_harness

    @pytest.mark.parametrize(
        ('field_name', 'make_draft'),
        [
            pytest.param('text', make_text_draft, id='text'),
            pytest.param('cite', make_cite_draft, id='cite'),
            pytest.param('rests_on', make_rests_on_draft, id='rests_on'),
            pytest.param('refute', make_refute_draft, id='refute'),
            pytest.param('diagram', make_diagram_draft, id='diagram'),
        ],
    )
    def test_secret_in_a_free_text_field_is_replaced_in_the_stored_entry(
        self, harness: CaseHarness, field_name: str, make_draft: Callable[[str], Draft]
    ) -> None:
        leaked = 'abcdefghijklmnop1234' if field_name == 'cite' else LEAKED

        added = harness.add(make_draft(leaked))

        [entry] = harness.entries
        stored = getattr(entry, field_name)
        assert leaked not in stored
        assert '[REDACTED:' in stored
        assert added.redactions == 1

    def test_a_scrubbed_diagram_keeps_its_line_breaks_and_the_rest_of_its_source(
        self, harness: CaseHarness
    ) -> None:
        harness.add(make_diagram_draft(LEAKED))

        [entry] = harness.entries
        assert entry.diagram == f'flowchart TD\n  A["{LEAK_MARK}"] --> B\n  B --> C'

    def test_a_clean_diagram_is_stored_as_it_came_and_counts_no_redaction(
        self, harness: CaseHarness
    ) -> None:
        diagram = 'flowchart TD\n  A["queue"] --> B["sleep"]'

        added = harness.add(replace(create_draft(), diagram=diagram))

        assert [entry.diagram for entry in harness.entries] == [diagram]
        assert added.redactions == 0

    def test_secret_in_a_supplied_quote_is_replaced_in_the_stored_entry(
        self, harness: CaseHarness
    ) -> None:
        added = harness.add(make_quote_draft(LEAKED))

        [entry] = harness.entries
        assert entry.quote == LEAK_MARK
        assert added.redactions == 1

    def test_secret_in_a_captured_quote_is_replaced_in_the_stored_entry(
        self, harness: CaseHarness
    ) -> None:
        draft = replace(create_valid_draft('known'), cite='src/config.py:2')

        added = harness.add(draft)

        [entry] = harness.entries
        assert LEAKED not in (entry.quote or '')
        assert LEAK_MARK in (entry.quote or '')
        assert added.redactions == 1

    def test_redactions_are_counted_across_the_batch(self, harness: CaseHarness) -> None:
        first = make_text_draft(f'key {LEAKED}')
        second = replace(create_draft(2), text='ok', rests_on=None)
        third = make_text_draft(f'again {LEAKED}')

        added = harness.add(first, second, third)

        assert added.redactions == 2
        assert all(LEAKED not in entry.text for entry in harness.entries)

    def test_clean_batch_reports_no_redactions(self, harness: CaseHarness) -> None:
        added = harness.add(make_text_draft('max_tokens=4096 stalls the queue'))

        assert added.redactions == 0
        assert [entry.text for entry in harness.entries] == ['max_tokens=4096 stalls the queue']
