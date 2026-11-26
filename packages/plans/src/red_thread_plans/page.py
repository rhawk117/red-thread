"""The plan as a page: each worktree's stack of tickets, marked by what changed since the last."""

from collections import Counter
from dataclasses import dataclass
from itertools import chain
from typing import TYPE_CHECKING

from red_thread_casefile.domain import date_of, shorten_head
from red_thread_core.charts import clean_label
from red_thread_core.documents import (
    CodeListing,
    Document,
    Fact,
    Flowchart,
    Paragraph,
    PointList,
    Section,
    parse_line,
)
from red_thread_core.util import squeeze

from red_thread_plans.assets import read_asset
from red_thread_plans.domain import Mitigate, YouIntervene
from red_thread_plans.nodes import TICKET_STATUSES, Promise, TicketList, TicketNode

if TYPE_CHECKING:
    from collections.abc import Mapping

    from red_thread_casefile.domain import Case
    from red_thread_core.documents import Line

    from red_thread_plans.domain import Acceptance, Handling, Plan, PlanIndex, Risk, Ticket
    from red_thread_plans.nodes import TicketStatus

STACK_NOTE = 'Bottom of the stack first: each ticket is one pull request on the one before it.'
MAP_NOTE = (
    'Each worktree as a stack, with an arrow from a ticket to each ticket that depends on it.'
)
CASES_NOTE = 'The investigations this plan rests on. A ref such as C1.e4 is entry e4 of case C1.'
DROPPED_NOTE = 'Tickets the revision before had and this one leaves out.'


def to_line(text: str) -> Line:
    return parse_line(squeeze(text))


def describe_handling(handling: Handling) -> str:
    if isinstance(handling, Mitigate):
        criterion = '' if handling.criterion is None else f' ({handling.criterion})'
        return f'mitigated by ticket {handling.ticket}{criterion}'

    if isinstance(handling, YouIntervene):
        return f'you intervene, and {", ".join(handling.recut)} would be cut again'

    return 'accepted'


def describe_risk(risk: Risk) -> Line:
    touched = ', '.join(risk.tickets) or 'no ticket'
    handled = describe_handling(risk.handling)
    return to_line(f'{risk.id}, {handled}: {risk.risk} Signal: {risk.signal} Touches {touched}.')


def compose_points(title: str, texts: tuple[str, ...]) -> tuple[Section, ...]:
    if not texts:
        return ()
    return (Section(title=title, blocks=(PointList(points=tuple(map(to_line, texts))),)),)


def create_promise(acceptance: Acceptance) -> Promise:
    return Promise(criterion=to_line(acceptance.criterion), required_by=acceptance.required_by)


def label_ticket(ticket: Ticket) -> str:
    return f'{ticket.id}: {clean_label(ticket.title)}'


@dataclass(slots=True, kw_only=True, frozen=True)
class PlanChanges:
    plan: Plan
    previous: Plan | None = None

    def mark(self, ticket: Ticket) -> TicketStatus:
        before = self.previous.find_ticket(ticket.id) if self.previous is not None else None
        if before is None:
            return 'new'
        return 'unchanged' if before == ticket else 'changed'

    @property
    def dropped(self) -> tuple[Ticket, ...]:
        if self.previous is None:
            return ()
        kept = {ticket.id for ticket in self.plan.tickets}
        return tuple(ticket for ticket in self.previous.tickets if ticket.id not in kept)

    def describe(self) -> str:
        if self.previous is None:
            return 'first revision'
        counted = Counter(map(self.mark, self.plan.tickets))
        marks = ', '.join(f'{counted[status]} {status}' for status in TICKET_STATUSES)
        return f'since revision {self.previous.revision}: {marks}, {len(self.dropped)} dropped'


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


@dataclass(slots=True, kw_only=True, frozen=True)
class PlanPage:
    index: PlanIndex
    cases: Mapping[str, Case]
    changes: PlanChanges

    @property
    def plan(self) -> Plan:
        return self.changes.plan

    def create_ticket(self, ticket: Ticket) -> TicketNode:
        interface = ticket.interface
        listing = (
            None
            if interface is None
            else CodeListing(language=interface.language, source=interface.source)
        )
        return TicketNode(
            id=ticket.id,
            title=to_line(ticket.title),
            why=to_line(ticket.why),
            worktree=ticket.worktree,
            position=ticket.position,
            status=self.changes.mark(ticket),
            acceptance=tuple(map(create_promise, ticket.acceptance)),
            owns=ticket.owns,
            depends_on=ticket.depends_on,
            interface=listing,
        )

    def compose_worktree(self, worktree: str) -> Section:
        tickets = TicketList(tickets=tuple(map(self.create_ticket, self.plan.stack(worktree))))
        return Section(title=f'Worktree {worktree}', blocks=(tickets,), note=STACK_NOTE)

    def compose_risks(self) -> tuple[Section, ...]:
        if not self.plan.risks:
            return ()
        risks = PointList(points=tuple(map(describe_risk, self.plan.risks)))
        return (Section(title='Risks', blocks=(risks,)),)

    def compose_appendix(self) -> tuple[Section, ...]:
        chart = Flowchart(lines=WorktreeMap(changes=self.changes).render())
        worktrees = Section(title='Worktrees', blocks=(chart,), note=MAP_NOTE)
        dropped = tuple(to_line(f'{ticket.id}: {ticket.title}') for ticket in self.changes.dropped)
        if not dropped:
            return (worktrees,)
        gone = Section(
            title='Dropped', blocks=(PointList(points=dropped),), note=DROPPED_NOTE, folded=True
        )
        return (worktrees, gone)

    def list_facts(self) -> tuple[Fact, ...]:
        plan = self.plan
        counted = f'{len(plan.tickets)} in {len(plan.worktrees)} worktrees'
        return (
            Fact(label='Revision', value=to_line(str(plan.revision))),
            Fact(label='Stored', value=to_line(date_of(plan.at))),
            Fact(label='Commit', value=to_line(shorten_head(plan.head))),
            Fact(label='Tickets', value=to_line(counted)),
            Fact(label='Changes', value=to_line(self.changes.describe()), wide=True),
        )

    def describe_case(self, alias: str) -> Line:
        case_id = self.plan.cases[alias]
        case = self.cases.get(alias)
        target = '(not found in .red-thread/)' if case is None else case.target
        return to_line(f'{alias}: {case_id}, {target}')

    def compose_cases(self) -> Section:
        points = PointList(points=tuple(map(self.describe_case, self.plan.cases)))
        return Section(title='Cases', blocks=(points,), note=CASES_NOTE)

    def compose(self) -> Document:
        plan = self.plan
        return Document(
            title=squeeze(plan.intent),
            summary=(to_line(f'Plan {self.index.id}: {self.index.title}'),),
            facts=self.list_facts(),
            sections=(
                Section(title='Approach', blocks=(Paragraph(line=to_line(plan.approach)),)),
                self.compose_cases(),
                *compose_points('Invariants', plan.invariants),
                *compose_points('Non-goals', plan.non_goals),
                *map(self.compose_worktree, plan.worktrees),
                *self.compose_risks(),
            ),
            appendix=self.compose_appendix(),
        )
