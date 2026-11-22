"""What the case file stamps on an entry and how it keeps the files append-only."""

from typing import TYPE_CHECKING

import pytest

from tests.casefile.batches.supersede_cases import seq_params
from tests.casefile.ledger.builders import create_draft, create_entry, create_valid_draft
from tests.casefile.ledger.memory import HEAD, MOMENT, NEXT_HEAD

if TYPE_CHECKING:
    from tests.casefile.batches.supersede_cases import SeqCase
    from tests.casefile.ledger.builders import CaseHarness


def seq_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', seq_params())


class TestStamping:
    @pytest.fixture
    def harness(self, framed_harness: CaseHarness) -> CaseHarness:
        framed_harness.seed(None, create_entry(seq=1), create_entry(seq=2))
        framed_harness.seed('T1', create_entry(seq=1), create_entry(seq=2))
        return framed_harness

    @seq_cases()
    def test_seq_counts_per_file(self, harness: CaseHarness, case: SeqCase) -> None:
        drafts = [create_draft(position) for position in range(1, case.count + 1)]

        added = harness.add(*drafts, thread=case.thread)

        assert [entry.ref for entry in added.entries] == list(case.refs)

    def test_round_time_and_head_are_stamped_on_every_entry(self, harness: CaseHarness) -> None:
        added = harness.add(create_draft(1), create_draft(2), create_draft(3), round_number=4)

        assert {entry.round for entry in added.entries} == {4}
        assert {entry.at for entry in added.entries} == {MOMENT}
        assert {entry.head for entry in added.entries} == {HEAD}

    def test_entry_stamped_without_a_commit_has_no_head(self, harness: CaseHarness) -> None:
        harness.tree.advance(None)

        added = harness.add(create_draft())

        assert [entry.head for entry in added.entries] == [None]

    def test_head_is_read_again_for_every_batch(self, harness: CaseHarness) -> None:
        first = harness.add(create_draft())
        harness.tree.advance(NEXT_HEAD)
        second = harness.add(create_draft())

        assert [entry.head for entry in first.entries] == [HEAD]
        assert [entry.head for entry in second.entries] == [NEXT_HEAD]
        stored = {entry.ref: entry.head for entry in harness.entries}
        assert (stored['e3'], stored['e4']) == (HEAD, NEXT_HEAD)

    def test_stored_entries_are_the_entries_returned(self, harness: CaseHarness) -> None:
        added = harness.add(create_valid_draft('known', 1), create_valid_draft('open', 2))

        assert set(added.entries) <= set(harness.entries)
        assert added.redactions == 0

    def test_add_keeps_every_entry_already_in_the_file(self, harness: CaseHarness) -> None:
        before = harness.entries

        harness.add(create_draft(), create_draft(2))
        harness.add(create_draft(), thread='T1')

        after = harness.entries
        assert all(entry in after for entry in before)
        assert len(after) == len(before) + 3
