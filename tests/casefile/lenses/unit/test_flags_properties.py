"""Annotator.list_flags: leads and citation findings flag a finding, whatever the heads are."""

from typing import TYPE_CHECKING

import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from red_thread_casefile.domain import SHORT_HEAD
from red_thread_casefile.policy import CitationCheck
from red_thread_casefile.views import NO_COMMIT, Annotator

from tests.casefile.findings.strategies import optional
from tests.casefile.ledger.builders import create_finding

if TYPE_CHECKING:
    from red_thread_casefile.policy import CitationState

HEAD = 'a1b2c3d4e5f60718293a4b5c6d7e8f9012345678'


def differ(heads: tuple[str | None, str | None]) -> bool:
    return heads[0] != heads[1]


class TestListFlags:
    commits = st.from_regex(r'[0-9a-f]{40}', fullmatch=True)
    heads = optional(commits)
    different_heads = st.tuples(heads, heads).filter(differ)
    failing = st.sampled_from(('changed', 'missing'))
    quiet = st.sampled_from(('ok', 'unchecked'))
    lines = st.integers(min_value=1, max_value=10**6)

    def list_flags(
        self, head: str | None, finding_head: str | None, *citation_checks: CitationCheck
    ) -> list[str]:
        finding = create_finding(finding_number=1, head=finding_head)
        return Annotator(head=head, citation_checks=citation_checks).list_flags(finding)

    @pytest.mark.regression
    @given(heads=different_heads)
    @example(heads=(None, HEAD))
    @example(heads=(HEAD, None))
    @example(heads=(HEAD, 'f' * 40))
    def test_an_finding_recorded_at_another_commit_is_flagged_as_a_lead_with_that_commit(
        self, heads: tuple[str | None, str | None]
    ) -> None:
        finding_head, head = heads
        recorded = NO_COMMIT if finding_head is None else finding_head[:SHORT_HEAD]

        flags = self.list_flags(head, finding_head)

        assert flags == [f'lead, recorded at {recorded}']

    @given(head=heads)
    def test_an_finding_recorded_at_the_current_commit_is_not_a_lead(
        self, head: str | None
    ) -> None:
        assert self.list_flags(head, head) == []

    @given(state=failing)
    def test_a_changed_or_missing_citation_is_flagged_with_its_state(
        self, state: CitationState
    ) -> None:
        citation_check = CitationCheck(finding_id='e1', citation='a.py:1', state=state)

        assert self.list_flags(HEAD, HEAD, citation_check) == [f'citation {state}']

    @given(state=quiet)
    def test_an_ok_or_unchecked_citation_is_not_flagged(self, state: CitationState) -> None:
        citation_check = CitationCheck(finding_id='e1', citation='a.py:1', state=state)

        assert self.list_flags(HEAD, HEAD, citation_check) == []

    @given(line=lines)
    def test_a_moved_citation_names_its_new_line(self, line: int) -> None:
        citation_check = CitationCheck(
            finding_id='e1', citation='a.py:1', state='moved', moved_to=line
        )

        assert self.list_flags(HEAD, HEAD, citation_check) == [f'citation moved to line {line}']

    @given(state=failing, line=lines)
    def test_a_citation_check_for_another_finding_flags_nothing(
        self, state: CitationState, line: int
    ) -> None:
        citation_check = CitationCheck(
            finding_id='e2', citation='a.py:1', state=state, moved_to=line
        )

        assert self.list_flags(HEAD, HEAD, citation_check) == []
