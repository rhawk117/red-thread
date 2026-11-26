"""What changed between two revisions: each ticket's mark and the fields that differ."""

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_plans.nodes import TICKET_STATUSES, FieldChange
from red_thread_plans.wording import describe_criterion, describe_risk

if TYPE_CHECKING:
    from collections.abc import Mapping

    from red_thread_plans.domain import Plan, Ticket
    from red_thread_plans.nodes import TicketStatus

type Described = dict[str, tuple[str, ...]]


def describe_ticket(ticket: Ticket) -> Described:
    interface = ticket.interface
    return {
        'title': (ticket.title,),
        'why': (ticket.why,),
        'worktree': (ticket.worktree,),
        'position': (str(ticket.position),),
        'depends on': ticket.depends_on,
        'owns': ticket.owns,
        'acceptance criteria': tuple(map(describe_criterion, ticket.acceptance)),
        'interface': () if interface is None else (interface.source,),
    }


def describe_plan(plan: Plan) -> Described:
    return {
        'intent': (plan.intent,),
        'approach': (plan.approach,),
        'cases': tuple(f'{alias}: {case_id}' for alias, case_id in plan.cases.items()),
        'invariants': plan.invariants,
        'non-goals': plan.non_goals,
        'risks': tuple(map(describe_risk, plan.risks)),
    }


def diff_values(field: str, old: tuple[str, ...], new: tuple[str, ...]) -> FieldChange | None:
    if old == new:
        return None
    removed = tuple(value for value in old if value not in new)
    added = tuple(value for value in new if value not in old)
    if not removed and not added:
        return FieldChange(field=field, removed=old, added=new)
    return FieldChange(field=field, removed=removed, added=added)


def compare_fields(
    before: Mapping[str, tuple[str, ...]], after: Described
) -> tuple[FieldChange, ...]:
    found = (diff_values(field, before[field], values) for field, values in after.items())
    return tuple(change for change in found if change is not None)


@dataclass(slots=True, kw_only=True, frozen=True)
class PlanChanges:
    plan: Plan
    previous: Plan | None = None

    def find_before(self, ticket: Ticket) -> Ticket | None:
        if self.previous is None:
            return None
        return self.previous.find_ticket(ticket.id)

    def mark(self, ticket: Ticket) -> TicketStatus:
        before = self.find_before(ticket)
        if before is None:
            return 'new'
        return 'unchanged' if before == ticket else 'changed'

    def compare_ticket(self, ticket: Ticket) -> tuple[FieldChange, ...]:
        before = self.find_before(ticket)
        if before is None:
            return ()
        return compare_fields(describe_ticket(before), describe_ticket(ticket))

    def compare_plan(self) -> tuple[FieldChange, ...]:
        if self.previous is None:
            return ()
        return compare_fields(describe_plan(self.previous), describe_plan(self.plan))

    @property
    def dropped(self) -> tuple[Ticket, ...]:
        if self.previous is None:
            return ()
        kept = {ticket.id for ticket in self.plan.tickets}
        return tuple(ticket for ticket in self.previous.tickets if ticket.id not in kept)

    def list_marked(self, status: TicketStatus) -> tuple[str, ...]:
        return tuple(ticket.id for ticket in self.plan.tickets if self.mark(ticket) == status)

    def list_moves(self) -> tuple[str, ...]:
        new = ', '.join(self.list_marked('new'))
        changed = ', '.join(self.list_marked('changed'))
        dropped = ', '.join(ticket.id for ticket in self.dropped)
        moves = (
            f'New tickets: {new}.' if new else '',
            f'Changed tickets: {changed}.' if changed else '',
            f'Dropped tickets: {dropped}.' if dropped else '',
        )
        return tuple(move for move in moves if move) or (
            'No ticket was added, changed or dropped.',
        )

    def describe(self) -> str:
        if self.previous is None:
            return 'first revision'
        counted = Counter(map(self.mark, self.plan.tickets))
        marks = ', '.join(f'{counted[status]} {status}' for status in TICKET_STATUSES)
        return f'since revision {self.previous.revision}: {marks}, {len(self.dropped)} dropped'
