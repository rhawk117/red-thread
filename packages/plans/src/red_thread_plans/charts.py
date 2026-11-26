"""The worktree chart: each worktree a stack, with an arrow from each dependency."""

from dataclasses import dataclass
from itertools import chain
from typing import TYPE_CHECKING

from red_thread_core.charts import clean_label

from red_thread_plans.assets import read_asset

if TYPE_CHECKING:
    from red_thread_plans.changes import PlanChanges
    from red_thread_plans.domain import Ticket


def label_ticket(ticket: Ticket) -> str:
    return f'{ticket.id}: {clean_label(ticket.title)}'


@dataclass(slots=True, kw_only=True, frozen=True)
class WorktreeMap:
    changes: PlanChanges

    @property
    def names(self) -> dict[str, str]:
        tickets = self.changes.plan.tickets
        return {ticket.id: f'n{index}' for index, ticket in enumerate(tickets)}

    def write_node(self, ticket: Ticket) -> str:
        name = self.names[ticket.id]
        return f'    {name}["{label_ticket(ticket)}"]:::s_{self.changes.mark(ticket)}'

    def write_worktree(self, index: int, worktree: str) -> list[str]:
        nodes = map(self.write_node, self.changes.plan.stack(worktree))
        return [f'  subgraph l{index}["{worktree}"]', *nodes, '  end']

    def write_dependencies(self, ticket: Ticket) -> list[str]:
        names = self.names
        return [f'  {names[need]} --> {names[ticket.id]}' for need in ticket.depends_on]

    def render(self) -> tuple[str, ...]:
        plan = self.changes.plan
        worktrees = chain.from_iterable(
            map(self.write_worktree, range(len(plan.worktrees)), plan.worktrees, strict=True)
        )
        edges = chain.from_iterable(map(self.write_dependencies, plan.tickets))
        return (read_asset('worktrees.mmd').rstrip(), *worktrees, *edges)
