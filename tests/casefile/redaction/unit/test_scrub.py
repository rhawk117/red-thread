"""The scrubber replaces and counts secrets, and check flags every entry field that holds one."""

import string
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis import strategies as st
from msgspec.structs import replace
from red_thread_casefile.errors import MisquotedCiteError, SecretInEntryError
from red_thread_core.redaction import create_secret_patterns

from tests.casefile.ledger.builders import create_entry, create_valid_entry
from tests.casefile.redaction.cases import LEAKED, ordinary_text_params, secret_params

if TYPE_CHECKING:
    from collections.abc import Callable

    from red_thread_casefile.domain import Entry
    from red_thread_casefile.errors import CaseFileError

    from tests.casefile.ledger.builders import CaseHarness
    from tests.casefile.redaction.cases import SecretCase

LEAK_MARK = '[REDACTED:aws-access-key]'
LEAK_LINE = f'AWS_KEY = "{LEAKED}"'
SCRUBBED_LINE = f'AWS_KEY = "{LEAK_MARK}"'


def make_text_entry(text: str) -> Entry:
    return replace(create_entry(), text=text)


def make_cite_entry(text: str) -> Entry:
    return replace(create_valid_entry('known'), cite=f'curl -H "Authorization: Bearer {text}"')


def make_rests_on_entry(text: str) -> Entry:
    return replace(create_entry(), verdict='INFERRED', rests_on=f'a note with {text}')


def make_refute_entry(text: str) -> Entry:
    return replace(create_valid_entry('hypothesis'), refute=f'a log showing {text}')


def make_quote_entry(text: str) -> Entry:
    return replace(create_valid_entry('known'), cite='src/config.py:2', quote=text)


def list_secrets(problems: tuple[CaseFileError, ...]) -> list[SecretInEntryError]:
    return [problem for problem in problems if isinstance(problem, SecretInEntryError)]


def make_diagram_entry(text: str) -> Entry:
    return replace(create_entry(), diagram=f'flowchart TD\n  A["{text}"] --> B\n  B --> C')


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


@pytest.fixture
def harness(framed_harness: CaseHarness) -> CaseHarness:
    framed_harness.tree.write('src/config.py', ('import os', LEAK_LINE))
    return framed_harness


class TestSecretInAField:
    @pytest.mark.parametrize(
        ('field_name', 'make_entry'),
        [
            pytest.param('text', make_text_entry, id='text'),
            pytest.param('cite', make_cite_entry, id='cite'),
            pytest.param('rests_on', make_rests_on_entry, id='rests_on'),
            pytest.param('refute', make_refute_entry, id='refute'),
            pytest.param('diagram', make_diagram_entry, id='diagram'),
        ],
    )
    def test_secret_in_a_free_text_field_is_a_fault_that_never_echoes_it(
        self, harness: CaseHarness, field_name: str, make_entry: Callable[[str], Entry]
    ) -> None:
        leaked = 'abcdefghijklmnop1234' if field_name == 'cite' else LEAKED
        harness.seed(None, make_entry(leaked))

        problems = harness.find_problems()

        assert [problem.field for problem in list_secrets(problems)] == [field_name]
        assert len(problems) == 1
        assert '[REDACTED:' in list_secrets(problems)[0].scrubbed
        assert leaked not in str(problems[0])

    def test_check_leaves_the_secret_where_it_was_written(self, harness: CaseHarness) -> None:
        harness.seed(None, make_text_entry(LEAKED))
        before = dict(harness.repository.files)

        harness.check()

        assert harness.repository.files == before
        assert LEAKED in harness.repository.files['case.md']

    def test_scrubbed_diagram_keeps_its_line_breaks_and_the_rest_of_its_source(
        self, harness: CaseHarness
    ) -> None:
        harness.seed(None, make_diagram_entry(LEAKED))

        [secret] = list_secrets(harness.find_problems())

        assert secret.scrubbed == f'flowchart TD\n  A["{LEAK_MARK}"] --> B\n  B --> C'

    def test_clean_diagram_is_no_fault(self, harness: CaseHarness) -> None:
        diagram = 'flowchart TD\n  A["queue"] --> B["sleep"]'
        harness.seed(None, replace(create_entry(), diagram=diagram))

        assert harness.find_problems() == ()


class TestWhereASecretIsFound:
    def test_quote_of_a_secret_line_as_written_is_a_secret_and_a_misquote(
        self, harness: CaseHarness
    ) -> None:
        harness.seed(None, make_quote_entry(LEAK_LINE))

        found = {type(problem) for problem in harness.find_problems()}

        assert found == {SecretInEntryError, MisquotedCiteError}

    def test_quote_of_a_secret_line_as_scrubbed_is_no_fault(self, harness: CaseHarness) -> None:
        harness.seed(None, make_quote_entry(SCRUBBED_LINE))

        assert harness.find_problems() == ()

    def test_every_field_holding_a_secret_is_its_own_fault(self, harness: CaseHarness) -> None:
        entry = replace(make_refute_entry(LEAKED), text=f'key {LEAKED}')
        harness.seed(None, entry)

        secrets = list_secrets(harness.find_problems())

        assert [secret.field for secret in secrets] == ['text', 'refute']

    def test_retired_entry_is_still_checked_for_secrets(self, harness: CaseHarness) -> None:
        retiring = replace(create_entry(seq=2), supersedes=('e1',))
        harness.seed(None, make_text_entry(f'key {LEAKED}'), retiring)

        secrets = list_secrets(harness.find_problems())

        assert [secret.spot.ref for secret in secrets] == ['e1']

    def test_secret_in_a_thread_file_is_named_by_that_file(self, harness: CaseHarness) -> None:
        harness.seed('T1', make_text_entry(f'key {LEAKED}'))

        secrets = list_secrets(harness.find_problems())

        assert [(secret.spot.file, secret.spot.ref) for secret in secrets] == [
            ('threads/T1.md', 'T1.e1')
        ]

    def test_clean_entry_is_no_fault(self, harness: CaseHarness) -> None:
        harness.seed(None, make_text_entry('max_tokens=4096 stalls the queue'))

        assert harness.find_problems() == ()
