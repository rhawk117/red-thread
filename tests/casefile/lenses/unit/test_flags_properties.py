"""Annotator.list_flags: leads and citation findings flag an entry, whatever the heads are."""

from typing import TYPE_CHECKING

import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from red_thread_casefile.domain import SHORT_HEAD
from red_thread_casefile.policy import Finding
from red_thread_casefile.views import NO_COMMIT, Annotator

from tests.casefile.entries.strategies import optional
from tests.casefile.ledger.builders import create_entry

if TYPE_CHECKING:
    from red_thread_casefile.policy import CiteState

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

    def list_flags(self, head: str | None, entry_head: str | None, *findings: Finding) -> list[str]:
        entry = create_entry(seq=1, head=entry_head)
        return Annotator(head=head, findings=findings).list_flags(entry)

    @pytest.mark.regression
    @given(heads=different_heads)
    @example(heads=(None, HEAD))
    @example(heads=(HEAD, None))
    @example(heads=(HEAD, 'f' * 40))
    def test_an_entry_recorded_at_another_commit_is_flagged_as_a_lead_with_that_commit(
        self, heads: tuple[str | None, str | None]
    ) -> None:
        entry_head, head = heads
        recorded = NO_COMMIT if entry_head is None else entry_head[:SHORT_HEAD]

        flags = self.list_flags(head, entry_head)

        assert flags == [f'lead, recorded at {recorded}']

    @given(head=heads)
    def test_an_entry_recorded_at_the_current_commit_is_not_a_lead(self, head: str | None) -> None:
        assert self.list_flags(head, head) == []

    @given(state=failing)
    def test_a_changed_or_missing_citation_is_flagged_with_its_state(
        self, state: CiteState
    ) -> None:
        finding = Finding(ref='e1', cite='a.py:1', state=state)

        assert self.list_flags(HEAD, HEAD, finding) == [f'citation {state}']

    @given(state=quiet)
    def test_an_ok_or_unchecked_citation_is_not_flagged(self, state: CiteState) -> None:
        finding = Finding(ref='e1', cite='a.py:1', state=state)

        assert self.list_flags(HEAD, HEAD, finding) == []

    @given(line=lines)
    def test_a_moved_citation_names_its_new_line(self, line: int) -> None:
        finding = Finding(ref='e1', cite='a.py:1', state='moved', moved_to=line)

        assert self.list_flags(HEAD, HEAD, finding) == [f'citation moved to line {line}']

    @given(state=failing, line=lines)
    def test_a_finding_for_another_entry_flags_nothing(self, state: CiteState, line: int) -> None:
        finding = Finding(ref='e2', cite='a.py:1', state=state, moved_to=line)

        assert self.list_flags(HEAD, HEAD, finding) == []
