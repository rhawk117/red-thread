"""The scrubber replaces and counts secrets, and check flags every finding field that holds one."""

import string
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.errors import MisquotedCitationError, SecretInFindingError
from red_thread_core.redaction import create_secret_patterns, grow_inside, trim_edges

from tests.casefile.ledger.builders import create_finding, create_valid_finding
from tests.casefile.redaction.cases import LEAKED, ordinary_text_params, secret_params

if TYPE_CHECKING:
    from collections.abc import Callable

    from red_thread_casefile.domain import CaseFinding
    from red_thread_casefile.errors import CaseFileError

    from tests.casefile.ledger.builders import CaseHarness
    from tests.casefile.redaction.cases import SecretCase

LEAK_MARK = '[REDACTED:aws-access-key]'
LEAK_LINE = f'AWS_KEY = "{LEAKED}"'
SCRUBBED_LINE = f'AWS_KEY = "{LEAK_MARK}"'


def make_text_finding(text: str) -> CaseFinding:
    return create_finding().replace_with(text=text)


def make_citation_finding(text: str) -> CaseFinding:
    return create_valid_finding('known').replace_with(
        citation=f'curl -H "Authorization: Bearer {text}"'
    )


def make_rests_on_finding(text: str) -> CaseFinding:
    return create_finding().replace_with(verdict='INFERRED', rests_on=f'a note with {text}')


def make_refute_finding(text: str) -> CaseFinding:
    return create_valid_finding('hypothesis').replace_with(refuted_if=f'a log showing {text}')


def make_quote_finding(text: str) -> CaseFinding:
    return create_valid_finding('known').replace_with(citation='src/config.py:2', quote=text)


def list_secrets(problems: tuple[CaseFileError, ...]) -> list[SecretInFindingError]:
    return [problem for problem in problems if isinstance(problem, SecretInFindingError)]


def make_diagram_finding(text: str) -> CaseFinding:
    return create_finding().replace_with(diagram=f'flowchart TD\n  A["{text}"] --> B\n  B --> C')


def secret_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', secret_params())


def ordinary_text_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('text', ordinary_text_params())


def edge_trim_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        ('text', 'span', 'expected'),
        [
            pytest.param('"abc"', (0, 5), (1, 4), id='quotes'),
            pytest.param(' abc ', (0, 5), (1, 4), id='spaces'),
            pytest.param('abc', (0, 3), (0, 3), id='nothing-to-trim'),
            pytest.param('  ', (0, 2), (2, 2), id='all-edge'),
        ],
    )


def inside_growth_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        ('text', 'span', 'expected'),
        [
            pytest.param('key=abc123;', (4, 7), (4, 10), id='grows-right-to-boundary'),
            pytest.param('xabc y', (1, 4), (0, 4), id='grows-left-to-start'),
            pytest.param('abc', (0, 3), (0, 3), id='whole-text'),
            pytest.param(' a ', (1, 2), (1, 2), id='bounded-by-boundaries'),
        ],
    )


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


class TestTrimEdges:
    @edge_trim_cases()
    def test_drops_edge_characters_from_both_ends(
        self, text: str, span: tuple[int, int], expected: tuple[int, int]
    ) -> None:
        assert trim_edges(text, span) == expected


class TestGrowInside:
    @inside_growth_cases()
    def test_extends_over_inside_characters_only(
        self, text: str, span: tuple[int, int], expected: tuple[int, int]
    ) -> None:
        assert grow_inside(text, span) == expected


@pytest.fixture
def harness(framed_harness: CaseHarness) -> CaseHarness:
    framed_harness.tree.write('src/config.py', ('import os', LEAK_LINE))
    return framed_harness


class TestSecretInAField:
    @pytest.mark.parametrize(
        ('field_name', 'make_finding'),
        [
            pytest.param('text', make_text_finding, id='text'),
            pytest.param('cite', make_citation_finding, id='cite'),
            pytest.param('rests_on', make_rests_on_finding, id='rests_on'),
            pytest.param('refute', make_refute_finding, id='refute'),
            pytest.param('diagram', make_diagram_finding, id='diagram'),
        ],
    )
    def test_secret_in_a_free_text_field_is_a_fault_that_never_echoes_it(
        self, harness: CaseHarness, field_name: str, make_finding: Callable[[str], CaseFinding]
    ) -> None:
        leaked = 'abcdefghijklmnop1234' if field_name == 'cite' else LEAKED
        harness.seed(None, make_finding(leaked))

        problems = harness.find_problems()

        assert [problem.field for problem in list_secrets(problems)] == [field_name]
        assert len(problems) == 1
        assert '[REDACTED:' in list_secrets(problems)[0].scrubbed
        assert leaked not in str(problems[0])

    def test_check_leaves_the_secret_where_it_was_written(self, harness: CaseHarness) -> None:
        harness.seed(None, make_text_finding(LEAKED))
        before = dict(harness.repository.files)

        harness.check()

        assert harness.repository.files == before
        assert LEAKED in harness.repository.files['case.md']

    def test_scrubbed_diagram_keeps_its_line_breaks_and_the_rest_of_its_source(
        self, harness: CaseHarness
    ) -> None:
        harness.seed(None, make_diagram_finding(LEAKED))

        [secret] = list_secrets(harness.find_problems())

        assert secret.scrubbed == f'flowchart TD\n  A["{LEAK_MARK}"] --> B\n  B --> C'

    def test_clean_diagram_is_no_fault(self, harness: CaseHarness) -> None:
        diagram = 'flowchart TD\n  A["queue"] --> B["sleep"]'
        harness.seed(None, create_finding().replace_with(diagram=diagram))

        assert harness.find_problems() == ()


class TestWhereASecretIsFound:
    def test_quote_of_a_secret_line_as_written_is_a_secret_and_a_misquote(
        self, harness: CaseHarness
    ) -> None:
        harness.seed(None, make_quote_finding(LEAK_LINE))

        found = {type(problem) for problem in harness.find_problems()}

        assert found == {SecretInFindingError, MisquotedCitationError}

    def test_quote_of_a_secret_line_as_scrubbed_is_no_fault(self, harness: CaseHarness) -> None:
        harness.seed(None, make_quote_finding(SCRUBBED_LINE))

        assert harness.find_problems() == ()

    def test_every_field_holding_a_secret_is_its_own_fault(self, harness: CaseHarness) -> None:
        finding = make_refute_finding(LEAKED).replace_with(text=f'key {LEAKED}')
        harness.seed(None, finding)

        secrets = list_secrets(harness.find_problems())

        assert [secret.field for secret in secrets] == ['text', 'refute']

    def test_retired_finding_is_still_checked_for_secrets(self, harness: CaseHarness) -> None:
        retiring = create_finding(finding_number=2).replace_with(supersedes=('e1',))
        harness.seed(None, make_text_finding(f'key {LEAKED}'), retiring)

        secrets = list_secrets(harness.find_problems())

        assert [secret.location.finding_id for secret in secrets] == ['e1']

    def test_secret_in_a_thread_file_is_named_by_that_file(self, harness: CaseHarness) -> None:
        harness.seed('T1', make_text_finding(f'key {LEAKED}'))

        secrets = list_secrets(harness.find_problems())

        assert [(secret.location.file, secret.location.finding_id) for secret in secrets] == [
            ('threads/T1.md', 'T1.e1')
        ]

    def test_clean_finding_is_no_fault(self, harness: CaseHarness) -> None:
        harness.seed(None, make_text_finding('max_tokens=4096 stalls the queue'))

        assert harness.find_problems() == ()
