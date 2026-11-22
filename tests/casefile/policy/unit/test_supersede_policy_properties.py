"""SupersedePolicy: unknown refs come first, then refs outside the draft's own thread."""

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.domain import Draft
from red_thread_casefile.errors import ForeignSupersededError, UnknownSupersededError
from red_thread_casefile.policy import SupersedePolicy

from tests.casefile.entries.strategies import POOLED_REFS

UNKNOWN = 'e999'
NAMED_THREADS = ('T1', 'T2', 'T10')


def create_draft(supersedes: list[str]) -> Draft:
    return Draft(
        position=3, kind='open', text='a lead', source='scout', supersedes=tuple(supersedes)
    )


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
    def test_known_refs_of_the_drafts_own_thread_are_accepted(
        self, thread: str | None, data: st.DataObject
    ) -> None:
        refs = data.draw(st.lists(st.sampled_from(list_own_refs(thread)), max_size=3))
        known = frozenset(refs) | data.draw(self.known_sets)

        problem = SupersedePolicy(
            draft=create_draft(refs), known_refs=known, thread=thread
        ).get_supersede_problem()

        assert problem is None

    @given(thread=threads, before=any_refs, after=any_refs, known=known_sets)
    def test_the_first_unknown_ref_is_named_even_when_another_ref_is_foreign(
        self, thread: str | None, before: list[str], after: list[str], known: frozenset[str]
    ) -> None:
        refs = [*(ref for ref in before if ref in known), UNKNOWN, *after]

        problem = SupersedePolicy(
            draft=create_draft(refs), known_refs=known, thread=thread
        ).get_supersede_problem()

        assert isinstance(problem, UnknownSupersededError)
        assert problem.ref == UNKNOWN
        assert problem.position == 3

    @given(thread=named_threads, data=st.data())
    def test_the_first_ref_outside_the_drafts_thread_is_named_when_all_refs_are_known(
        self, thread: str, data: st.DataObject
    ) -> None:
        own = list_own_refs(thread)
        outside = [ref for ref in POOLED_REFS if ref not in own]
        before = data.draw(st.lists(st.sampled_from(own), max_size=2))
        first = data.draw(st.sampled_from(outside))
        after = data.draw(self.any_refs)

        problem = SupersedePolicy(
            draft=create_draft([*before, first, *after]),
            known_refs=frozenset(POOLED_REFS),
            thread=thread,
        ).get_supersede_problem()

        assert isinstance(problem, ForeignSupersededError)
        assert (problem.ref, problem.thread, problem.position) == (first, thread, 3)
