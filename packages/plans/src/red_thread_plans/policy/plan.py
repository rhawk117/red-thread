"""What makes a whole drafted plan storable: its ids, its dependencies, its lanes and every item."""

from dataclasses import dataclass
from itertools import chain, combinations, product
from typing import TYPE_CHECKING

from red_thread_plans.domain import Claim
from red_thread_plans.errors import (
    BlankPlanTextError,
    CrossLaneDependencyError,
    DependencyCycleError,
    DuplicatePlanIdError,
    LaneCollisionError,
    NoTicketsError,
    UnknownDependencyError,
)
from red_thread_plans.policy.items import (
    RiskPolicy,
    TicketPolicy,
    describe_owned_fault,
    find_duplicates,
    get_blank_problems,
)
from red_thread_plans.util import find_cycle, find_shared_path

if TYPE_CHECKING:
    from red_thread_casefile.errors import CaseFileError

    from red_thread_plans.domain import PlanDraft, TicketDraft
    from red_thread_plans.policy.items import Grounds, Problems


@dataclass(slots=True, kw_only=True, frozen=True)
class GraphPolicy:
    drafted: tuple[TicketDraft, ...]

    @property
    def tickets(self) -> dict[str, TicketDraft]:
        return {ticket.id: ticket for ticket in self.drafted}

    @property
    def lanes(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(ticket.lane for ticket in self.drafted))

    def get_dependency_problem(self, ticket: TicketDraft) -> CaseFileError | None:
        tickets = self.tickets
        unknown = next((name for name in ticket.depends_on if name not in tickets), None)
        if unknown is not None:
            return UnknownDependencyError(ticket=ticket.id, dependency=unknown)

        dependencies = (tickets[name] for name in ticket.depends_on)
        crossing = next((other for other in dependencies if other.lane != ticket.lane), None)
        if crossing is None:
            return None
        return CrossLaneDependencyError(ticket=ticket, dependency=crossing)

    def get_cycle_problem(self) -> DependencyCycleError | None:
        tickets = self.tickets
        graph = {
            name: [other for other in ticket.depends_on if other in tickets]
            for name, ticket in tickets.items()
        }
        cycle = find_cycle(graph)
        if cycle is None:
            return None
        return DependencyCycleError(cycle=cycle)

    def list_claims(self, lane: str) -> tuple[Claim, ...]:
        in_lane = (ticket for ticket in self.drafted if ticket.lane == lane)
        return tuple(
            Claim(lane=lane, ticket=ticket.id, owned=owned)
            for ticket in in_lane
            for owned in ticket.owns
            if describe_owned_fault(owned) is None
        )

    def get_collision_problem(self, first: str, second: str) -> LaneCollisionError | None:
        pairs = product(self.list_claims(first), self.list_claims(second))
        found = ((left, right, find_shared_path(left.owned, right.owned)) for left, right in pairs)
        return next(
            (
                LaneCollisionError(first=left, second=right, example=example)
                for left, right, example in found
                if example is not None
            ),
            None,
        )

    def get_lane_issues(self) -> Problems:
        found = (self.get_collision_problem(*pair) for pair in combinations(self.lanes, 2))
        return tuple(filter(None, found))

    def get_graph_issues(self) -> Problems:
        dependencies = map(self.get_dependency_problem, self.drafted)
        found = (*dependencies, self.get_cycle_problem())
        return (*filter(None, found), *self.get_lane_issues())


@dataclass(slots=True, kw_only=True, frozen=True)
class PlanPolicy:
    draft: PlanDraft
    grounds: Grounds

    @property
    def graph(self) -> GraphPolicy:
        return GraphPolicy(drafted=self.draft.tickets)

    def get_text_issues(self) -> Problems:
        intent = BlankPlanTextError(field='intent') if not self.draft.intent.strip() else None
        approach = BlankPlanTextError(field='approach') if not self.draft.approach.strip() else None
        invariants = get_blank_problems('invariant', self.draft.invariants)
        non_goals = get_blank_problems('non-goal', self.draft.non_goals)
        return (*filter(None, (intent, approach)), *invariants, *non_goals)

    def get_id_issues(self) -> Problems:
        empty = () if self.draft.tickets else (NoTicketsError(),)
        ticket_ids = find_duplicates(ticket.id for ticket in self.draft.tickets)
        risk_ids = find_duplicates(risk.id for risk in self.draft.risks)
        tickets = (DuplicatePlanIdError(field='ticket', value=value) for value in ticket_ids)
        risks = (DuplicatePlanIdError(field='risk', value=value) for value in risk_ids)
        return (*empty, *tickets, *risks)

    def get_item_issues(self) -> Problems:
        tickets = self.graph.tickets
        ticket_policies = (
            TicketPolicy(ticket=ticket, grounds=self.grounds) for ticket in self.draft.tickets
        )
        risk_policies = (RiskPolicy(risk=risk, tickets=tickets) for risk in self.draft.risks)
        ticket_issues = (policy.get_ticket_issues() for policy in ticket_policies)
        risk_issues = (policy.get_risk_issues() for policy in risk_policies)
        return tuple(chain.from_iterable((*ticket_issues, *risk_issues)))

    def get_plan_issues(self) -> Problems:
        return (
            *self.get_text_issues(),
            *self.get_id_issues(),
            *self.get_item_issues(),
            *self.graph.get_graph_issues(),
        )
