"""SupersedePolicy: unknown finding ids come first, then ids outside the finding's own thread."""

from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.domain import FindingLocation
from red_thread_casefile.errors import ForeignSupersededError, UnknownSupersededError
from red_thread_casefile.policy import SupersedePolicy

from tests.casefile.findings.strategies import POOLED_REFS
from tests.casefile.ledger.builders import create_finding

if TYPE_CHECKING:
    from red_thread_casefile.domain import CaseFinding

UNKNOWN = 'e999'
NAMED_THREADS = ('T1', 'T2', 'T10')
LOCATION = FindingLocation(file='case.md', line=12, finding_id='e3')


def create_superseding(finding_ids: list[str], thread: str | None) -> CaseFinding:
    return create_finding(
        finding_number=3, text='a lead', supersedes=tuple(finding_ids), thread=thread
    )


def list_own_finding_ids(thread: str | None) -> list[str]:
    if thread is None:
        return list(POOLED_REFS)
    return [finding_id for finding_id in POOLED_REFS if finding_id.startswith(f'{thread}.')]


class TestSupersedePolicyProperties:
    threads = st.sampled_from((None, *NAMED_THREADS))
    named_threads = st.sampled_from(NAMED_THREADS)
    any_finding_ids = st.lists(st.sampled_from(POOLED_REFS), max_size=3)
    known_sets = st.frozensets(st.sampled_from(POOLED_REFS))

    @given(thread=threads, data=st.data())
    def test_known_finding_ids_of_the_entrys_own_thread_are_accepted(
        self, thread: str | None, data: st.DataObject
    ) -> None:
        finding_ids = data.draw(st.lists(st.sampled_from(list_own_finding_ids(thread)), max_size=3))
        known = frozenset(finding_ids) | data.draw(self.known_sets)

        problem = SupersedePolicy(
            finding=create_superseding(finding_ids, thread),
            location=LOCATION,
            known_finding_ids=known,
        ).get_supersede_problem()

        assert not problem

    @given(thread=threads, before=any_finding_ids, after=any_finding_ids, known=known_sets)
    def test_the_first_unknown_finding_id_is_named_even_when_another_finding_id_is_foreign(
        self, thread: str | None, before: list[str], after: list[str], known: frozenset[str]
    ) -> None:
        finding_ids = [
            *(finding_id for finding_id in before if finding_id in known),
            UNKNOWN,
            *after,
        ]

        problem = SupersedePolicy(
            finding=create_superseding(finding_ids, thread),
            location=LOCATION,
            known_finding_ids=known,
        ).get_supersede_problem()

        assert isinstance(problem, UnknownSupersededError)
        assert problem.finding_id == UNKNOWN
        assert problem.location == LOCATION

    @given(thread=named_threads, data=st.data())
    def test_the_first_finding_id_outside_the_entrys_thread_is_named_when_all_finding_ids_are_known(
        self, thread: str, data: st.DataObject
    ) -> None:
        own = list_own_finding_ids(thread)
        outside = [finding_id for finding_id in POOLED_REFS if finding_id not in own]
        before = data.draw(st.lists(st.sampled_from(own), max_size=2))
        first = data.draw(st.sampled_from(outside))
        after = data.draw(self.any_finding_ids)

        problem = SupersedePolicy(
            finding=create_superseding([*before, first, *after], thread),
            location=LOCATION,
            known_finding_ids=frozenset(POOLED_REFS),
        ).get_supersede_problem()

        assert isinstance(problem, ForeignSupersededError)
        assert (problem.finding_id, problem.thread, problem.location) == (first, thread, LOCATION)
