"""SupersedePolicy: unknown refs come first, then refs outside the entry's own thread."""

from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.domain import Spot
from red_thread_casefile.errors import ForeignSupersededError, UnknownSupersededError
from red_thread_casefile.policy import SupersedePolicy

from tests.casefile.entries.strategies import POOLED_REFS
from tests.casefile.ledger.builders import create_entry

if TYPE_CHECKING:
    from red_thread_casefile.domain import Entry

UNKNOWN = 'e999'
NAMED_THREADS = ('T1', 'T2', 'T10')
SPOT = Spot(file='case.md', line=12, ref='e3')


def create_superseding(refs: list[str], thread: str | None) -> Entry:
    return create_entry(seq=3, text='a lead', supersedes=tuple(refs), thread=thread)


def list_own_refs(thread: str | None) -> list[str]:
    if thread is None:
        return list(POOLED_REFS)
    return [ref for ref in POOLED_REFS if ref.startswith(f'{thread}.')]


class TestSupersedePolicyProperties:
    threads = st.sampled_from((None, *NAMED_THREADS))
    named_threads = st.sampled_from(NAMED_THREADS)
    any_refs = st.lists(st.sampled_from(POOLED_REFS), max_size=3)
    known_sets = st.frozensets(st.sampled_from(POOLED_REFS))

    @given(thread=threads, data=st.data())
    def test_known_refs_of_the_entrys_own_thread_are_accepted(
        self, thread: str | None, data: st.DataObject
    ) -> None:
        refs = data.draw(st.lists(st.sampled_from(list_own_refs(thread)), max_size=3))
        known = frozenset(refs) | data.draw(self.known_sets)

        problem = SupersedePolicy(
            entry=create_superseding(refs, thread), spot=SPOT, known_refs=known
        ).get_supersede_problem()

        assert not problem

    @given(thread=threads, before=any_refs, after=any_refs, known=known_sets)
    def test_the_first_unknown_ref_is_named_even_when_another_ref_is_foreign(
        self, thread: str | None, before: list[str], after: list[str], known: frozenset[str]
    ) -> None:
        refs = [*(ref for ref in before if ref in known), UNKNOWN, *after]

        problem = SupersedePolicy(
            entry=create_superseding(refs, thread), spot=SPOT, known_refs=known
        ).get_supersede_problem()

        assert isinstance(problem, UnknownSupersededError)
        assert problem.ref == UNKNOWN
        assert problem.spot == SPOT

    @given(thread=named_threads, data=st.data())
    def test_the_first_ref_outside_the_entrys_thread_is_named_when_all_refs_are_known(
        self, thread: str, data: st.DataObject
    ) -> None:
        own = list_own_refs(thread)
        outside = [ref for ref in POOLED_REFS if ref not in own]
        before = data.draw(st.lists(st.sampled_from(own), max_size=2))
        first = data.draw(st.sampled_from(outside))
        after = data.draw(self.any_refs)

        problem = SupersedePolicy(
            entry=create_superseding([*before, first, *after], thread),
            spot=SPOT,
            known_refs=frozenset(POOLED_REFS),
        ).get_supersede_problem()

        assert isinstance(problem, ForeignSupersededError)
        assert (problem.ref, problem.thread, problem.spot) == (first, thread, SPOT)
