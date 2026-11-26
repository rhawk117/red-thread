"""Planner.propose: a sound plan becomes the next revision, a refused one leaves nothing behind."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from msgspec.structs import replace
from red_thread_casefile.plans.errors import PlanRejectedError
from red_thread_casefile.plans.util import order_stack
from red_thread_casefile.services import Planner

from tests.casefile.ledger.memory import HEAD, MOMENT
from tests.casefile.plans.builders import (
    create_resting_ledger,
    create_valid_draft,
    plant_collision,
    plant_cycle,
    plant_groundless,
)
from tests.casefile.plans.memory import MemoryPlanRepository
from tests.casefile.plans.strategies import valid_plans
from tests.casefile.redaction.strategies import planted_secrets
from tests.casefile.services.fakes import create_service_harness

if TYPE_CHECKING:
    from red_thread_casefile.plans.domain import Plan, PlanDraft

    from tests.casefile.redaction.strategies import Planted


@dataclass(slots=True, kw_only=True, frozen=True)
class PlannerHarness:
    plans: MemoryPlanRepository
    planner: Planner


def create_planner_harness() -> PlannerHarness:
    service = create_service_harness()
    service.seed(*create_resting_ledger().entries)
    plans = MemoryPlanRepository()
    return PlannerHarness(plans=plans, planner=Planner(record=service.case_file, plans=plans))


def list_lane_positions(plan: Plan, lane: str) -> list[int]:
    return [ticket.position for ticket in plan.stack(lane)]


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
        faulty = plant_collision(plant_cycle(plant_groundless(create_valid_draft(), 2)), 0)

        with pytest.raises(PlanRejectedError) as refused:
            harness.planner.propose(faulty)

        assert len(refused.value.problems) == 3
        assert harness.plans.revisions == (1,)

    @given(plan=valid_plans)
    def test_each_lane_is_numbered_from_one_in_stack_order(self, plan: PlanDraft) -> None:
        stored = create_planner_harness().planner.propose(plan)

        for lane in stored.plan.lanes:
            in_lane = tuple(ticket for ticket in plan.tickets if ticket.lane == lane)
            stack = tuple(ticket.id for ticket in stored.plan.stack(lane))
            assert stack == order_stack(in_lane)
            assert list_lane_positions(stored.plan, lane) == list(range(1, len(stack) + 1))

    @given(planted=planted_secrets)
    def test_a_secret_in_the_plan_is_redacted_before_it_is_stored(self, planted: Planted) -> None:
        harness = create_planner_harness()
        draft = replace(create_valid_draft(), intent=f'rotate {planted.whole}')

        stored = harness.planner.propose(draft)

        assert stored.plan.intent == f'rotate {planted.redacted}'
        assert stored.redactions == 1
