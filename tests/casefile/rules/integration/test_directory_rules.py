"""Checking the findings of a real case directory in a real git repository."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.errors import (
    OwnerInThreadError,
    SecretInFindingError,
    UncitedKnownError,
)

from tests.casefile.ledger.builders import create_finding, create_valid_finding
from tests.casefile.redaction.cases import LEAKED
from tests.casefile.rules.places import place_finding

if TYPE_CHECKING:
    from tests.casefile.ledger.directory import DirectoryHarness


class TestCheckOnADirectory:
    @pytest.fixture
    def harness(self, framed_directory_harness: DirectoryHarness) -> DirectoryHarness:
        return framed_directory_harness

    @pytest.fixture
    def faulty_harness(self, harness: DirectoryHarness) -> DirectoryHarness:
        harness.seed(
            None,
            create_valid_finding('open', 1),
            create_valid_finding('known', 2).replace_with(citation=None),
        )
        harness.seed('T1', create_valid_finding('open', 1).replace_with(source='user'))
        return harness

    def test_each_fault_is_named_by_the_file_that_holds_it(
        self, faulty_harness: DirectoryHarness
    ) -> None:
        case_text = faulty_harness.case_file.read_text(encoding='utf-8')
        thread_text = faulty_harness.thread_file('T1').read_text(encoding='utf-8')
        expected = (
            (UncitedKnownError, place_finding(case_text, None, 2)),
            (OwnerInThreadError, place_finding(thread_text, 'T1', 1)),
        )

        problems = faulty_harness.check().problems

        assert [type(problem) for problem in problems] == [kind for kind, _ in expected]
        named = zip(map(str, problems), expected, strict=True)
        assert all(text.startswith(place) for text, (_, place) in named)

    def test_check_leaves_every_file_byte_for_byte(self, faulty_harness: DirectoryHarness) -> None:
        files = (faulty_harness.case_file, faulty_harness.thread_file('T1'))
        before = [path.read_bytes() for path in files]

        faulty_harness.check()

        assert [path.read_bytes() for path in files] == before

    def test_retiring_an_finding_keeps_both_findings(self, harness: DirectoryHarness) -> None:
        harness.seed(
            None,
            create_valid_finding('open', 1),
            create_finding(finding_number=2, supersedes=('e1',)),
        )

        ledger = harness.casefile.load().ledger

        assert harness.check().problems == ()
        assert [finding.finding_id for finding in ledger.live] == ['e2']
        assert len(ledger.findings) == 2

    def test_each_thread_file_counts_its_own_findings(self, harness: DirectoryHarness) -> None:
        harness.seed(None, create_finding())
        harness.seed('T1', create_finding(finding_number=1), create_finding(finding_number=2))
        harness.seed('T2', create_finding())

        ledger = harness.casefile.load().ledger

        assert harness.check().problems == ()
        assert sorted(finding.finding_id for finding in ledger.findings) == [
            'T1.e1',
            'T1.e2',
            'T2.e1',
            'e1',
        ]

    def test_secret_is_a_fault_and_stays_where_it_was_written(
        self, harness: DirectoryHarness
    ) -> None:
        harness.git.write('src/config.py', f'import os\nAWS_KEY = "{LEAKED}"\n')
        finding = create_valid_finding('known').replace_with(
            text=f'the key {LEAKED} is committed',
            citation='src/config.py:2',
            quote='AWS_KEY = "[REDACTED:aws-access-key]"',
        )
        harness.seed(None, finding)

        problems = harness.check().problems

        secrets = [problem for problem in problems if isinstance(problem, SecretInFindingError)]
        assert len(problems) == 1
        assert [problem.field for problem in secrets] == ['text']
        assert LEAKED not in str(problems[0])
        assert LEAKED in harness.case_file.read_text(encoding='utf-8')
