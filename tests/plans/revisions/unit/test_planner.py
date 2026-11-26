"""The planner: a plan opens once, a sound draft is the next revision, a refused one is dropped."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from msgspec.structs import replace
from red_thread_core.places import link_board
from red_thread_plans.domain import CaseRecord, Opening, cite_cases
from red_thread_plans.errors import (
    NoRevisionError,
    PlanExistsError,
    PlanRejectedError,
    UnknownCaseError,
)
from red_thread_plans.services import Planner
from red_thread_plans.util import order_stack

from tests.casefile.ledger.builders import CASE_ID, create_case
from tests.casefile.ledger.memory import (
    HEAD,
    MOMENT,
    FixedClock,
    MemoryPageStore,
    MemorySourceTree,
)
from tests.casefile.redaction.strategies import planted_secrets
from tests.plans.revisions.builders import (
    PLAN_INDEX,
    create_resting_ledger,
    create_valid_draft,
    plant_collision,
    plant_cycle,
    plant_groundless,
)
from tests.plans.revisions.memory import MemoryCaseShelf, MemoryPlanRepository
from tests.plans.revisions.strategies import valid_plans

if TYPE_CHECKING:
    from red_thread_plans.domain import Plan, PlanDraft

    from tests.casefile.redaction.strategies import Planted


@dataclass(slots=True, kw_only=True, frozen=True)
class PlannerHarness:
    plans: MemoryPlanRepository
    pages: MemoryPageStore
    planner: Planner


def create_planner_harness() -> PlannerHarness:
    record = CaseRecord(case=create_case(), ledger=create_resting_ledger())
    plans = MemoryPlanRepository(indexes=[PLAN_INDEX])
    pages = MemoryPageStore()
    planner = Planner(
        shelf=MemoryCaseShelf(records={CASE_ID: record}),
        plans=plans,
        pages=pages,
        tree=MemorySourceTree(),
        clock=FixedClock(),
    )
    return PlannerHarness(plans=plans, pages=pages, planner=planner)


def list_worktree_positions(plan: Plan, worktree: str) -> list[int]:
    return [ticket.position for ticket in plan.stack(worktree)]


class TestPlanner:
    @pytest.fixture
    def harness(self) -> PlannerHarness:
        return create_planner_harness()

    def test_the_first_plan_is_revision_one_stamped_with_the_clock_and_head(
        self, harness: PlannerHarness
    ) -> None:
        stored = harness.planner.propose(create_valid_draft())

        assert (stored.plan.revision, stored.plan.at, stored.plan.head) == (1, MOMENT, HEAD)
        assert stored.path.name == 'r1.json'
        assert harness.plans.revisions == (1,)

    def test_each_stored_revision_redraws_the_plan_page_against_the_one_before(
        self, harness: PlannerHarness
    ) -> None:
        harness.planner.propose(create_valid_draft())

        stored = harness.planner.propose(replace(create_valid_draft(), intent='a second cut'))

        assert stored.page.name == 'plan.html'
        page = harness.pages.files['plan.html']
        assert 'since revision 1: 0 new, 0 changed, 3 unchanged, 0 dropped' in page

    def test_each_later_plan_is_the_next_revision_and_leaves_the_earlier_one(
        self, harness: PlannerHarness
    ) -> None:
        first = harness.planner.propose(create_valid_draft())
        second = harness.planner.propose(replace(create_valid_draft(), intent='a second cut'))

        assert second.plan.revision == 2
        assert harness.plans.read_plans() == (first.plan, second.plan)

    def test_a_refused_plan_names_every_fault_and_stores_nothing(
        self, harness: PlannerHarness
    ) -> None:
        harness.planner.propose(create_valid_draft())
        drawn = harness.pages.files['plan.html']
        faulty = plant_collision(plant_cycle(plant_groundless(create_valid_draft(), 2)), 0)

        with pytest.raises(PlanRejectedError) as refused:
            harness.planner.propose(faulty)

        assert len(refused.value.problems) == 3
        assert harness.plans.revisions == (1,)
        assert harness.pages.files['plan.html'] == drawn

    @given(plan=valid_plans)
    def test_each_worktree_is_numbered_from_one_in_stack_order(self, plan: PlanDraft) -> None:
        stored = create_planner_harness().planner.propose(plan)

        for worktree in stored.plan.worktrees:
            in_worktree = tuple(ticket for ticket in plan.tickets if ticket.worktree == worktree)
            stack = tuple(ticket.id for ticket in stored.plan.stack(worktree))
            assert stack == order_stack(in_worktree)
            assert list_worktree_positions(stored.plan, worktree) == list(range(1, len(stack) + 1))

    @given(planted=planted_secrets)
    def test_a_secret_in_the_plan_is_redacted_before_it_is_stored(self, planted: Planted) -> None:
        harness = create_planner_harness()
        draft = replace(create_valid_draft(), intent=f'rotate {planted.whole}')

        stored = harness.planner.propose(draft)

        assert stored.plan.intent == f'rotate {planted.redacted}'
        assert stored.redactions == 1

    def test_a_stored_revision_adds_its_cases_to_the_plan_index(
        self, harness: PlannerHarness
    ) -> None:
        harness.planner.propose(create_valid_draft())

        assert harness.plans.read_index() == cite_cases(PLAN_INDEX, (CASE_ID,))

    def test_a_case_alias_that_names_no_case_is_refused(self, harness: PlannerHarness) -> None:
        draft = replace(create_valid_draft(), cases={'C1': CASE_ID, 'C2': 'no-such-case'})

        with pytest.raises(PlanRejectedError) as refused:
            harness.planner.propose(draft)

        assert [type(problem) for problem in refused.value.problems] == [UnknownCaseError]
        assert harness.plans.revisions == ()


class TestRedraw:
    @pytest.fixture
    def harness(self) -> PlannerHarness:
        return create_planner_harness()

    def test_render_redraws_the_page_of_the_latest_revision(self, harness: PlannerHarness) -> None:
        harness.planner.propose(create_valid_draft())
        harness.pages.files.clear()

        page = harness.planner.redraw()

        assert page.name == 'plan.html'
        assert link_board(CASE_ID) in harness.pages.files['plan.html']

    def test_render_without_a_revision_is_refused(self, harness: PlannerHarness) -> None:
        with pytest.raises(NoRevisionError):
            harness.planner.redraw()


class TestOpenPlan:
    opening = Opening(id='20261121-ship-it', title='ship it')

    @pytest.fixture
    def harness(self) -> PlannerHarness:
        plans = MemoryPlanRepository()
        planner = Planner(
            shelf=MemoryCaseShelf(),
            plans=plans,
            pages=MemoryPageStore(),
            tree=MemorySourceTree(),
            clock=FixedClock(),
        )
        return PlannerHarness(plans=plans, pages=MemoryPageStore(), planner=planner)

    def test_a_new_plan_has_an_index_with_no_case_yet(self, harness: PlannerHarness) -> None:
        index = harness.planner.open(self.opening)

        assert (index.id, index.title, index.at, index.cases) == (
            self.opening.id,
            'ship it',
            MOMENT,
            (),
        )
        assert harness.plans.read_index() == index

    def test_a_plan_is_opened_only_once(self, harness: PlannerHarness) -> None:
        harness.planner.open(self.opening)

        with pytest.raises(PlanExistsError):
            harness.planner.open(self.opening)

        assert len(harness.plans.indexes) == 1
