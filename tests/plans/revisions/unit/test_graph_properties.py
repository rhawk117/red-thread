"""order_stack and find_cycle: a stack puts each dependency first, and a reported cycle is real."""

from itertools import pairwise
from typing import TYPE_CHECKING

from hypothesis import example, given
from hypothesis import strategies as st
from red_thread_plans.domain import TicketDraft
from red_thread_plans.util import find_cycle, order_stack

from tests.plans.revisions.strategies import valid_plans

if TYPE_CHECKING:
    from red_thread_plans.domain import PlanDraft

NODES = ('t0', 't1', 't2', 't3', 't4')


def create_node(ticket_id: str, depends_on: list[str]) -> TicketDraft:
    return TicketDraft(id=ticket_id, title=ticket_id, lane='core', depends_on=tuple(depends_on))


def create_graph(edges: list[list[str]]) -> tuple[TicketDraft, ...]:
    return tuple(map(create_node, NODES, edges, strict=True))


def map_dependencies(tickets: tuple[TicketDraft, ...]) -> dict[str, tuple[str, ...]]:
    return {ticket.id: ticket.depends_on for ticket in tickets}


def is_ordered(stack: tuple[str, ...], tickets: tuple[TicketDraft, ...]) -> bool:
    place = {ticket_id: number for number, ticket_id in enumerate(stack)}
    return all(place[need] < place[ticket.id] for ticket in tickets for need in ticket.depends_on)


graphs = st.lists(
    st.lists(st.sampled_from(NODES), max_size=2, unique=True),
    min_size=len(NODES),
    max_size=len(NODES),
).map(create_graph)


@given(plan=valid_plans)
def test_a_stack_holds_every_ticket_once_after_its_dependencies(plan: PlanDraft) -> None:
    stack = order_stack(plan.tickets)

    assert sorted(stack) == sorted(ticket.id for ticket in plan.tickets)
    assert is_ordered(stack, plan.tickets)


@given(plan=valid_plans)
def test_tickets_without_dependencies_keep_the_order_they_were_drafted_in(plan: PlanDraft) -> None:
    free = tuple(
        TicketDraft(id=ticket.id, title=ticket.title, lane=ticket.lane) for ticket in plan.tickets
    )

    assert order_stack(free) == tuple(ticket.id for ticket in plan.tickets)


@given(plan=valid_plans)
def test_a_valid_plan_has_no_cycle(plan: PlanDraft) -> None:
    assert find_cycle(map_dependencies(plan.tickets)) is None


@given(tickets=graphs)
@example(tickets=create_graph([['t1'], ['t0'], [], [], []]))
@example(tickets=create_graph([['t0'], [], [], [], []]))
def test_a_cycle_is_found_exactly_when_no_stack_holds_every_ticket(
    tickets: tuple[TicketDraft, ...],
) -> None:
    cycle = find_cycle(map_dependencies(tickets))

    assert (cycle is None) == (len(order_stack(tickets)) == len(tickets))


@given(tickets=graphs)
@example(tickets=create_graph([['t1'], ['t2'], ['t0'], [], []]))
def test_a_reported_cycle_closes_and_each_ticket_depends_on_the_next(
    tickets: tuple[TicketDraft, ...],
) -> None:
    graph = map_dependencies(tickets)
    cycle = find_cycle(graph) or ()

    assert not cycle or cycle[0] == cycle[-1]
    assert all(after in graph[before] for before, after in pairwise(cycle))
