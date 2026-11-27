"""CaseLedger: live findings, selection, rounds, thread counts and thread order over pooled ids."""

from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.domain import FINDING_KINDS, CaseLedger

from tests.casefile.findings.strategies import POOLED_THREADS, finding_kinds, pooled_findings

if TYPE_CHECKING:
    from red_thread_casefile.domain import FindingKind


class TestLedger:
    ledgers = st.builds(
        CaseLedger, findings=st.builds(tuple, st.lists(pooled_findings, max_size=12))
    )

    @given(ledger=ledgers)
    def test_live_is_every_finding_no_finding_retires_in_ledger_order(
        self, ledger: CaseLedger
    ) -> None:
        named = {finding_id for finding in ledger.findings for finding_id in finding.supersedes}

        assert all(finding.finding_id not in named for finding in ledger.live)
        assert list(ledger.live) == [e for e in ledger.findings if e.finding_id not in named]

    @given(ledger=ledgers, kind=finding_kinds)
    def test_select_is_the_live_findings_of_that_kind(
        self, ledger: CaseLedger, kind: FindingKind
    ) -> None:
        selected = ledger.select(kind)

        assert all(finding in ledger.live for finding in selected)
        assert all(finding.kind == kind for finding in selected)
        assert list(selected) == [finding for finding in ledger.live if finding.kind == kind]

    @given(ledger=ledgers)
    def test_every_live_finding_is_selected_under_exactly_one_kind(
        self, ledger: CaseLedger
    ) -> None:
        assert sum(len(ledger.select(kind)) for kind in FINDING_KINDS) == len(ledger.live)

    @given(ledger=ledgers)
    def test_last_round_is_the_highest_round_or_zero(self, ledger: CaseLedger) -> None:
        rounds = [finding.round for finding in ledger.findings]

        assert ledger.last_round == max(rounds, default=0)

    @given(ledger=ledgers)
    def test_count_in_counts_the_findings_of_each_thread(self, ledger: CaseLedger) -> None:
        for thread in POOLED_THREADS:
            assert ledger.count_in(thread) == len([
                e for e in ledger.findings if e.thread == thread
            ])

        assert sum(ledger.count_in(thread) for thread in POOLED_THREADS) == len(ledger.findings)
        assert ledger.count_in('T99') == 0

    @given(ledger=ledgers)
    def test_threads_are_the_named_threads_in_numeric_order(self, ledger: CaseLedger) -> None:
        numbers = [int(name[1:]) for name in ledger.threads]

        assert numbers == sorted(set(numbers))
        assert set(ledger.threads) == {e.thread for e in ledger.findings if e.thread is not None}
