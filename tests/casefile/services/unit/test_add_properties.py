"""CaseFile.add: stamps consecutive seqs per thread, refuses whole batches, counts redactions."""

from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.domain import THREAD_NAME, Draft
from red_thread_casefile.errors import (
    BatchRejectedError,
    InvalidFieldError,
    InvalidThreadError,
    UncitedKnownError,
)
from red_thread_casefile.services import Batch

from tests.casefile.entries.strategies import POOLED_THREADS, words
from tests.casefile.ledger.memory import HEAD, MOMENT
from tests.casefile.redaction.strategies import planted_secrets
from tests.casefile.services.fakes import create_service_harness

if TYPE_CHECKING:
    from red_thread_casefile.domain import Entry

    from tests.casefile.redaction.strategies import Planted
    from tests.casefile.services.fakes import ServiceHarness


def create_batch(thread: str | None, texts: list[str], round_number: int) -> Batch:
    drafts = tuple(
        Draft(position=position, kind='open', text=text, source='scout')
        for position, text in enumerate(texts, 1)
    )
    return Batch(drafts=drafts, round=round_number, thread=thread)


def is_not_thread_name(name: str) -> bool:
    return THREAD_NAME.fullmatch(name) is None


def insert_uncited_known(batch: Batch, index: int) -> Batch:
    bad = Draft(position=index + 1, kind='known', text='unproven', source='scout')
    drafts = [*batch.drafts[:index], bad, *batch.drafts[index:]]
    renumbered = tuple(
        Draft(position=number, kind=draft.kind, text=draft.text, source=draft.source)
        for number, draft in enumerate(drafts, 1)
    )
    return Batch(drafts=renumbered, round=batch.round, thread=batch.thread)


class TestAddProperties:
    threads = st.sampled_from(POOLED_THREADS)
    batches = st.builds(
        create_batch,
        threads,
        st.lists(words, min_size=1, max_size=4),
        st.integers(min_value=0, max_value=5),
    )
    batch_runs = st.lists(batches, min_size=1, max_size=6)
    bad_threads = st.text(max_size=8).filter(is_not_thread_name)
    secret_groups = st.lists(st.lists(planted_secrets, max_size=3), min_size=1, max_size=3)

    def stock(self, *batches: Batch) -> ServiceHarness:
        harness = create_service_harness()
        for batch in batches:
            harness.case_file.add(batch)
        return harness

    @given(run=batch_runs)
    def test_each_batch_continues_the_seq_of_its_thread_from_the_entries_already_there(
        self, run: list[Batch]
    ) -> None:
        harness = create_service_harness()

        for batch in run:
            before = harness.store.read_ledger().count_in(batch.thread)
            added = harness.case_file.add(batch)

            first = before + 1
            assert [entry.seq for entry in added.entries] == list(
                range(first, first + len(batch.drafts))
            )
            assert [entry.text for entry in added.entries] == [d.text for d in batch.drafts]
            assert {
                (entry.thread, entry.round, entry.at, entry.head) for entry in added.entries
            } == {(batch.thread, batch.round, MOMENT, HEAD)}

    @given(run=batch_runs)
    def test_refs_never_collide_across_successive_batches(self, run: list[Batch]) -> None:
        harness = self.stock(*run)

        ledger = harness.store.read_ledger()

        assert len(ledger.refs) == len(ledger.entries)
        for thread in POOLED_THREADS:
            seqs = [entry.seq for entry in ledger.entries if entry.thread == thread]
            assert seqs == list(range(1, len(seqs) + 1))

    @given(run=batch_runs, batch=batches, data=st.data())
    def test_a_batch_with_one_rejected_draft_appends_nothing_and_names_that_draft(
        self, run: list[Batch], batch: Batch, data: st.DataObject
    ) -> None:
        harness = self.stock(*run)
        before = harness.read_entries()
        index = data.draw(st.integers(min_value=0, max_value=len(batch.drafts)))

        with pytest.raises(BatchRejectedError) as raised:
            harness.case_file.add(insert_uncited_known(batch, index))

        (problem,) = raised.value.problems
        assert isinstance(problem, UncitedKnownError)
        assert problem.position == index + 1
        assert harness.read_entries() == before

    @given(run=batch_runs, batch=batches)
    def test_a_batch_carrying_shape_problems_appends_nothing(
        self, run: list[Batch], batch: Batch
    ) -> None:
        harness = self.stock(*run)
        before = harness.read_entries()
        shape = InvalidFieldError(position=1, field='kind', expected='one of the kinds')
        flawed = Batch(
            drafts=batch.drafts, round=batch.round, thread=batch.thread, problems=(shape,)
        )

        with pytest.raises(BatchRejectedError) as raised:
            harness.case_file.add(flawed)

        assert raised.value.problems == (shape,)
        assert harness.read_entries() == before

    @given(run=batch_runs, batch=batches, thread=bad_threads)
    def test_a_thread_name_that_is_not_a_thread_appends_nothing(
        self, run: list[Batch], batch: Batch, thread: str
    ) -> None:
        harness = self.stock(*run)
        before = harness.read_entries()
        misplaced = Batch(drafts=batch.drafts, round=batch.round, thread=thread)

        with pytest.raises(InvalidThreadError):
            harness.case_file.add(misplaced)

        assert harness.read_entries() == before

    @given(groups=secret_groups)
    def test_redactions_count_the_secrets_planted_in_every_text_field(
        self, groups: list[list[Planted]]
    ) -> None:
        drafts = tuple(
            Draft(
                position=position,
                kind='open',
                text=f'note {" ".join(p.whole for p in group)}',
                source='scout',
                rests_on=f'on {" ".join(p.whole for p in group)}',
                diagram=f'flowchart TD\n  A {" ".join(p.whole for p in group)}',
            )
            for position, group in enumerate(groups, 1)
        )
        harness = create_service_harness()

        added = harness.case_file.add(Batch(drafts=drafts, round=1))

        stored: tuple[Entry, ...] = harness.read_entries()
        assert added.redactions == 3 * sum(len(group) for group in groups)
        assert [entry.text for entry in stored] == [
            f'note {" ".join(p.redacted for p in group)}' for group in groups
        ]
        assert [entry.rests_on for entry in stored] == [
            f'on {" ".join(p.redacted for p in group)}' for group in groups
        ]
        assert [entry.diagram for entry in stored] == [
            f'flowchart TD\n  A {" ".join(p.redacted for p in group)}' for group in groups
        ]
