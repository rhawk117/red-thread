"""The plan as a page: why, what changed, each worktree's tickets and the cases behind them."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_casefile.domain import date_of, shorten_head
from red_thread_core.documents import (
    CodeListing,
    Document,
    Fact,
    Flowchart,
    Link,
    Paragraph,
    PointList,
    Section,
    Text,
)
from red_thread_core.places import link_board
from red_thread_core.util import squeeze

from red_thread_plans.charts import WorktreeMap
from red_thread_plans.nodes import ChangeList, Ground, Promise, TicketList, TicketNode
from red_thread_plans.terms import PLAN_TERMS
from red_thread_plans.wording import describe_lights, describe_risk, to_line
from red_thread_plans.writers import NOT_PUBLISHED

if TYPE_CHECKING:
    from collections.abc import Mapping

    from red_thread_casefile.domain import Entry, Ledger
    from red_thread_core.documents import Line

    from red_thread_plans.changes import PlanChanges
    from red_thread_plans.domain import Acceptance, CaseRecord, Plan, PlanIndex, Ticket

STACK_NOTE = 'Bottom of the stack first: each ticket is one pull request on the one before it.'
MAP_NOTE = (
    'Each worktree as a stack, with an arrow from a ticket to each ticket that depends on it.'
)
CASES_NOTE = 'The investigations this plan rests on. A ref such as C1.e4 is entry e4 of case C1.'
CHANGES_NOTE = 'What this revision adds, changes or drops against the revision before.'
DROPPED_NOTE = 'Tickets the revision before had and this one leaves out.'
MISSING_GROUND = 'This entry is no longer in the case.'
MISSING_CASE = 'not found in .red-thread/'


def compose_points(title: str, texts: tuple[str, ...]) -> tuple[Section, ...]:
    if not texts:
        return ()
    return (Section(title=title, blocks=(PointList(points=tuple(map(to_line, texts))),)),)


def find_entry(ledger: Ledger, ref: str) -> Entry | None:
    return next((entry for entry in ledger.entries if entry.ref == ref), None)


def create_link(url: str | None, label: str) -> Line:
    if url is None:
        return to_line(NOT_PUBLISHED)
    return (Link(url=url, label=label),)


@dataclass(slots=True, kw_only=True, frozen=True)
class TicketComposer:
    index: PlanIndex
    records: Mapping[str, CaseRecord]
    changes: PlanChanges

    def find_ground(self, ref: str) -> Ground:
        alias, _, local = ref.partition('.')
        record = self.records.get(alias)
        entry = None if record is None else find_entry(record.ledger, local)
        if record is None or entry is None:
            return Ground(ref=ref, kind=None, claim=to_line(MISSING_GROUND))
        url = link_board(record.case.id, local)
        return Ground(ref=ref, kind=entry.kind, claim=to_line(entry.text), url=url)

    def create_promise(self, acceptance: Acceptance) -> Promise:
        grounds = tuple(map(self.find_ground, acceptance.required_by))
        return Promise(criterion=to_line(acceptance.criterion), grounds=grounds)

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
            acceptance=tuple(map(self.create_promise, ticket.acceptance)),
            owns=ticket.owns,
            depends_on=ticket.depends_on,
            interface=listing,
            changes=self.changes.compare_ticket(ticket),
            issue=self.index.find_issue(ticket.id),
        )


@dataclass(slots=True, kw_only=True, frozen=True)
class PlanPage:
    index: PlanIndex
    records: Mapping[str, CaseRecord]
    changes: PlanChanges

    @property
    def plan(self) -> Plan:
        return self.changes.plan

    @property
    def composer(self) -> TicketComposer:
        return TicketComposer(index=self.index, records=self.records, changes=self.changes)

    def compose_worktree(self, worktree: str) -> Section:
        create = self.composer.create_ticket
        tickets = TicketList(tickets=tuple(map(create, self.plan.stack(worktree))))
        return Section(
            title=f'Worktree {worktree}', blocks=(tickets,), note=STACK_NOTE, column=True
        )

    def compose_changes(self) -> tuple[Section, ...]:
        if self.changes.previous is None:
            return ()
        moves = PointList(points=tuple(map(to_line, self.changes.list_moves())))
        fields = ChangeList(changes=self.changes.compare_plan())
        return (Section(title='What changed', blocks=(moves, fields), note=CHANGES_NOTE),)

    def compose_risks(self) -> tuple[Section, ...]:
        if not self.plan.risks:
            return ()
        risks = PointList(points=tuple(to_line(describe_risk(risk)) for risk in self.plan.risks))
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
            Fact(label='Lights', value=to_line(describe_lights(plan.lights)), wide=True),
            Fact(label='Changes', value=to_line(self.changes.describe()), wide=True),
            Fact(label='Epic', value=create_link(self.index.epic, 'epic'), wide=True),
        )

    def describe_case(self, alias: str) -> Line:
        case_id = self.plan.cases[alias]
        record = self.records.get(alias)
        if record is None:
            return to_line(f'{alias}: {case_id}, {MISSING_CASE}')
        board = Link(url=link_board(case_id), label=case_id)
        return (Text(value=f'{alias}: '), board, Text(value=f', {squeeze(record.case.target)}'))

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
                *self.compose_changes(),
                Section(title='Approach', blocks=(Paragraph(line=to_line(plan.approach)),)),
                self.compose_cases(),
                *compose_points('Invariants', plan.invariants),
                *compose_points('Non-goals', plan.non_goals),
                *map(self.compose_worktree, plan.worktrees),
                *self.compose_risks(),
            ),
            appendix=self.compose_appendix(),
            terms=PLAN_TERMS,
        )
