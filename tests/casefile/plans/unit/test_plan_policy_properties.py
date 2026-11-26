"""PlanPolicy over every valid plan: no issue, and each planted fault named alone with its facts."""

from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.plans.errors import (
    DependencyCycleError,
    GroundlessAcceptanceError,
    LaneCollisionError,
)
from red_thread_casefile.plans.policy import PlanPolicy

from tests.casefile.plans.builders import (
    INTRUDER,
    LOOP,
    ROGUE_LANE,
    create_resting_grounds,
    plant_collision,
    plant_cycle,
    plant_groundless,
)
from tests.casefile.plans.strategies import matches_owned, valid_plans

if TYPE_CHECKING:
    from red_thread_casefile.errors import CaseFileError
    from red_thread_casefile.plans.domain import PlanDraft


class TestPlanPolicyProperties:
    grounds = create_resting_grounds()
    picks = st.integers(min_value=0, max_value=20)

    def find_issues(self, draft: PlanDraft) -> tuple[CaseFileError, ...]:
        return PlanPolicy(draft=draft, grounds=self.grounds).get_plan_issues()

    def find_only(self, draft: PlanDraft) -> CaseFileError:
        issues = self.find_issues(draft)
        assert len(issues) == 1, issues
        return issues[0]

    @given(plan=valid_plans)
    def test_a_valid_plan_has_no_issue(self, plan: PlanDraft) -> None:
        assert self.find_issues(plan) == ()

    @given(plan=valid_plans, pick=picks)
    def test_a_sentence_resting_on_nothing_is_named_by_ticket_and_number(
        self, plan: PlanDraft, pick: int
    ) -> None:
        index = pick % len(plan.tickets)

        issue = self.find_only(plant_groundless(plan, index))

        assert isinstance(issue, GroundlessAcceptanceError)
        assert (issue.sentence.ticket, issue.sentence.number) == (plan.tickets[index].id, 1)

    @given(plan=valid_plans)
    def test_a_planted_cycle_is_named_with_its_tickets_in_order(self, plan: PlanDraft) -> None:
        issue = self.find_only(plant_cycle(plan))

        assert isinstance(issue, DependencyCycleError)
        assert issue.cycle in {(*LOOP, LOOP[0]), (LOOP[1], LOOP[0], LOOP[1])}

    @given(plan=valid_plans, pick=picks)
    def test_two_lanes_owning_one_path_are_named_with_a_path_both_own(
        self, plan: PlanDraft, pick: int
    ) -> None:
        index = pick % len(plan.tickets)

        issue = self.find_only(plant_collision(plan, index))

        assert isinstance(issue, LaneCollisionError)
        assert {issue.first.lane, issue.second.lane} == {plan.tickets[index].lane, ROGUE_LANE}
        assert INTRUDER in {issue.first.ticket, issue.second.ticket}
        assert matches_owned(issue.example, issue.first.owned)
        assert matches_owned(issue.example, issue.second.owned)

    @given(plan=valid_plans, pick=picks)
    def test_every_planted_fault_is_named_in_one_pass(self, plan: PlanDraft, pick: int) -> None:
        index = pick % len(plan.tickets)
        faulty = plant_collision(plant_cycle(plant_groundless(plan, index)), index)

        named = {type(issue) for issue in self.find_issues(faulty)}

        assert named == {GroundlessAcceptanceError, DependencyCycleError, LaneCollisionError}
