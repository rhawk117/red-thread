"""Adding batches to a real case directory in a real git repository."""

import json
from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.errors import BatchRejectedError

from tests.casefile.ledger.builders import create_draft, create_valid_draft
from tests.casefile.ledger.directory import create_framed_directory_harness
from tests.casefile.redaction.cases import LEAKED

if TYPE_CHECKING:
    from tests.casefile.ledger.directory import DirectoryHarness
    from tests.casefile.ledger.git_repository import GitRepository


class TestAddToDirectory:
    @pytest.fixture
    def harness(self, framed_directory_harness: DirectoryHarness) -> DirectoryHarness:
        return framed_directory_harness

    def test_rejected_batch_writes_nothing(self, harness: DirectoryHarness) -> None:
        good = create_valid_draft('open', 1)
        bad = replace(create_valid_draft('known', 2), cite=None)

        with pytest.raises(BatchRejectedError):
            harness.add(good, bad)
        with pytest.raises(BatchRejectedError):
            harness.add(good, bad, thread='T1')

        assert not harness.ledger_file.exists()
        assert not harness.thread_file('T1').exists()

    def test_rejected_batch_leaves_an_existing_file_byte_for_byte(
        self, harness: DirectoryHarness
    ) -> None:
        harness.add(create_valid_draft('open'))
        before = harness.ledger_file.read_bytes()

        with pytest.raises(BatchRejectedError):
            harness.add(create_valid_draft('open', 1), replace(create_draft(2), verdict='INFERRED'))

        assert harness.ledger_file.read_bytes() == before

    def test_second_batch_only_appends_to_the_bytes_of_the_first(
        self, harness: DirectoryHarness
    ) -> None:
        harness.add(create_valid_draft('open', 1), create_valid_draft('known', 2))
        before = harness.ledger_file.read_bytes()

        harness.add(create_valid_draft('hypothesis'))

        after = harness.ledger_file.read_bytes()
        assert after.startswith(before)
        assert after[len(before) :].count(b'\n') == 1

    def test_retiring_an_entry_adds_a_line_and_edits_none(self, harness: DirectoryHarness) -> None:
        harness.add(create_valid_draft('open'))
        before = harness.ledger_file.read_bytes()

        harness.add(replace(create_draft(), supersedes=('e1',)))

        assert harness.ledger_file.read_bytes().startswith(before)
        ledger = harness.repository.read_ledger()
        assert [entry.ref for entry in ledger.live] == ['e2']
        assert len(ledger.entries) == 2

    def test_each_thread_writes_its_own_file_and_counts_its_own_seq(
        self, harness: DirectoryHarness
    ) -> None:
        harness.add(create_draft())
        harness.add(create_draft(), create_draft(2), thread='T1')
        harness.add(create_draft(), thread='T2')

        ledger = harness.repository.read_ledger()

        assert sorted(entry.ref for entry in ledger.entries) == ['T1.e1', 'T1.e2', 'T2.e1', 'e1']
        thread_lines = harness.thread_file('T1').read_text(encoding='utf-8').splitlines()
        assert [json.loads(line)['seq'] for line in thread_lines] == [1, 2]
        assert len(harness.ledger_file.read_text(encoding='utf-8').splitlines()) == 1

    def test_entries_are_stamped_with_the_real_head_and_never_a_later_one(
        self, harness: DirectoryHarness
    ) -> None:
        first_head = harness.git.head
        harness.add(create_draft())
        harness.git.write('src/other.py', 'x = 1\n')
        second_head = harness.git.commit('add other')

        harness.add(create_draft())

        heads = {entry.ref: entry.head for entry in harness.repository.read_ledger().entries}
        assert heads == {'e1': first_head, 'e2': second_head}
        assert first_head != second_head

    def test_entry_in_a_repository_with_no_commit_has_no_head(
        self, empty_repository: GitRepository
    ) -> None:
        harness = create_framed_directory_harness(empty_repository)

        harness.add(create_draft())

        [line] = harness.ledger_file.read_text(encoding='utf-8').splitlines()
        assert 'head' not in json.loads(line)

    def test_secret_never_reaches_the_file(self, harness: DirectoryHarness) -> None:
        harness.git.write('src/config.py', f'import os\nAWS_KEY = "{LEAKED}"\n')
        draft = replace(
            create_valid_draft('known'),
            text=f'the key {LEAKED} is committed',
            cite='src/config.py:2',
        )

        added = harness.add(draft)

        assert added.redactions == 2
        stored = harness.ledger_file.read_text(encoding='utf-8')
        assert LEAKED not in stored
        assert stored.count('[REDACTED:aws-key]') == 2
