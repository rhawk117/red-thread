"""Checking the entries of a real case directory in a real git repository."""

from typing import TYPE_CHECKING

import pytest
from msgspec.structs import replace
from red_thread_casefile.errors import (
    OwnerInThreadError,
    SecretInEntryError,
    UncitedKnownError,
)

from tests.casefile.ledger.builders import create_entry, create_valid_entry
from tests.casefile.redaction.cases import LEAKED
from tests.casefile.rules.places import place_entry

if TYPE_CHECKING:
    from tests.casefile.ledger.directory import DirectoryHarness


class TestCheckOnADirectory:
    @pytest.fixture
    def harness(self, framed_directory_harness: DirectoryHarness) -> DirectoryHarness:
        return framed_directory_harness

    @pytest.fixture
    def faulty_harness(self, harness: DirectoryHarness) -> DirectoryHarness:
        harness.seed(
            None, create_valid_entry('open', 1), replace(create_valid_entry('known', 2), cite=None)
        )
        harness.seed('T1', replace(create_valid_entry('open', 1), source='user'))
        return harness

    def test_each_fault_is_named_by_the_file_that_holds_it(
        self, faulty_harness: DirectoryHarness
    ) -> None:
        case_text = faulty_harness.case_file.read_text(encoding='utf-8')
        thread_text = faulty_harness.thread_file('T1').read_text(encoding='utf-8')
        expected = (
            (UncitedKnownError, place_entry(case_text, None, 2)),
            (OwnerInThreadError, place_entry(thread_text, 'T1', 1)),
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

    def test_retiring_an_entry_keeps_both_entries(self, harness: DirectoryHarness) -> None:
        harness.seed(None, create_valid_entry('open', 1), create_entry(seq=2, supersedes=('e1',)))

        ledger = harness.casefile.load().ledger

        assert harness.check().problems == ()
        assert [entry.ref for entry in ledger.live] == ['e2']
        assert len(ledger.entries) == 2

    def test_each_thread_file_counts_its_own_entries(self, harness: DirectoryHarness) -> None:
        harness.seed(None, create_entry())
        harness.seed('T1', create_entry(seq=1), create_entry(seq=2))
        harness.seed('T2', create_entry())

        ledger = harness.casefile.load().ledger

        assert harness.check().problems == ()
        assert sorted(entry.ref for entry in ledger.entries) == ['T1.e1', 'T1.e2', 'T2.e1', 'e1']

    def test_secret_is_a_fault_and_stays_where_it_was_written(
        self, harness: DirectoryHarness
    ) -> None:
        harness.git.write('src/config.py', f'import os\nAWS_KEY = "{LEAKED}"\n')
        entry = replace(
            create_valid_entry('known'),
            text=f'the key {LEAKED} is committed',
            cite='src/config.py:2',
            quote='AWS_KEY = "[REDACTED:aws-access-key]"',
        )
        harness.seed(None, entry)

        problems = harness.check().problems

        secrets = [problem for problem in problems if isinstance(problem, SecretInEntryError)]
        assert len(problems) == 1
        assert [problem.field for problem in secrets] == ['text']
        assert LEAKED not in str(problems[0])
        assert LEAKED in harness.case_file.read_text(encoding='utf-8')
