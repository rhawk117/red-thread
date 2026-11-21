"""Ledger: live entries, selection, rounds, thread counts and thread order over pooled refs."""

from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.domain import ENTRY_KINDS, Ledger

from tests.casefile.entries.strategies import POOLED_THREADS, entry_kinds, pooled_entries

if TYPE_CHECKING:
    from red_thread_casefile.domain import EntryKind


class TestLedger:
    ledgers = st.builds(Ledger, entries=st.builds(tuple, st.lists(pooled_entries, max_size=12)))

    @given(ledger=ledgers)
    def test_live_is_every_entry_no_entry_retires_in_ledger_order(self, ledger: Ledger) -> None:
        named = {ref for entry in ledger.entries for ref in entry.supersedes}

        assert all(entry.ref not in named for entry in ledger.live)
        assert list(ledger.live) == [e for e in ledger.entries if e.ref not in named]

    @given(ledger=ledgers, kind=entry_kinds)
    def test_select_is_the_live_entries_of_that_kind(self, ledger: Ledger, kind: EntryKind) -> None:
        selected = ledger.select(kind)

        assert all(entry in ledger.live for entry in selected)
        assert all(entry.kind == kind for entry in selected)
        assert list(selected) == [entry for entry in ledger.live if entry.kind == kind]

    @given(ledger=ledgers)
    def test_every_live_entry_is_selected_under_exactly_one_kind(self, ledger: Ledger) -> None:
        assert sum(len(ledger.select(kind)) for kind in ENTRY_KINDS) == len(ledger.live)

    @given(ledger=ledgers)
    def test_last_round_is_the_highest_round_or_zero(self, ledger: Ledger) -> None:
        rounds = [entry.round for entry in ledger.entries]

        assert ledger.last_round == max(rounds, default=0)

    @given(ledger=ledgers)
    def test_count_in_counts_the_entries_of_each_thread(self, ledger: Ledger) -> None:
        for thread in POOLED_THREADS:
            assert ledger.count_in(thread) == len([e for e in ledger.entries if e.thread == thread])

        assert sum(ledger.count_in(thread) for thread in POOLED_THREADS) == len(ledger.entries)
        assert ledger.count_in('T99') == 0

    @given(ledger=ledgers)
    def test_threads_are_the_named_threads_in_numeric_order(self, ledger: Ledger) -> None:
        numbers = [int(name[1:]) for name in ledger.threads]

        assert numbers == sorted(set(numbers))
        assert set(ledger.threads) == {e.thread for e in ledger.entries if e.thread is not None}
