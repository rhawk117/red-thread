"""A ledger to rest a plan on, a plan that passes every check and the faults planted in one."""

from typing import TYPE_CHECKING

from msgspec.structs import replace
from red_thread_casefile.domain import Ledger
from red_thread_plans.domain import Acceptance, PlanDraft, PlanIndex, TicketDraft
from red_thread_plans.page import PlanChanges, PlanPage
from red_thread_plans.policy import create_grounds
from red_thread_plans.services import RevisionStamp

from tests.casefile.ledger.builders import CASE_ID, URL_CITE, create_case, create_entry
from tests.casefile.ledger.memory import HEAD, MOMENT

if TYPE_CHECKING:
    from red_thread_core.documents import Document
    from red_thread_plans.domain import Plan
    from red_thread_plans.policy import Grounds

WORKTREES = ('core', 'docs', 'web')
ALIAS = 'C1'
RESTING_REFS = ('C1.e1', 'C1.e2')
OPEN_REF = 'C1.e3'
RETIRED_REF = 'C1.e4'
UNKNOWN_REF = 'C1.e99'
PLAN_ID = '20261121-give-a-case-a-plan'
PLAN_INDEX = PlanIndex(id=PLAN_ID, title='give a case a plan', at=MOMENT)
LOOP = ('loop-a', 'loop-b')
INTRUDER = 'intruder'
ROGUE_WORKTREE = 'rogue'


def create_resting_ledger() -> Ledger:
    return Ledger(
        entries=(
            create_entry(seq=1, kind='decision', text='keep one writer', source='user'),
            create_entry(seq=2, kind='known', text='the store is append only', cite=URL_CITE),
            create_entry(seq=3, kind='open', text='who reads the plan'),
            create_entry(seq=4, kind='decision', text='ship it later', source='user'),
            create_entry(
                seq=5, kind='decision', text='ship it now', source='user', supersedes=('e4',)
            ),
        )
    )


def create_resting_grounds() -> Grounds:
    return create_grounds({ALIAS: create_resting_ledger()})


def create_ticket_draft(ticket_id: str, worktree: str, owns: tuple[str, ...]) -> TicketDraft:
    return TicketDraft(
        id=ticket_id,
        title=f'build {ticket_id}',
        why=f'the plan needs {ticket_id}',
        worktree=worktree,
        acceptance=(Acceptance(criterion=f'{ticket_id} holds', required_by=RESTING_REFS),),
        owns=owns,
    )


def create_valid_draft(case_id: str = CASE_ID) -> PlanDraft:
    record = create_ticket_draft('plan-record', 'core', ('core/plans/',))
    page = replace(
        create_ticket_draft('plan-page', 'core', ('core/pages/*.py',)),
        depends_on=('plan-record',),
    )
    docs = create_ticket_draft('docs', 'docs', ('docs/**/*.md',))
    return PlanDraft(
        intent='give a case a plan',
        approach='store it beside the ledger',
        cases={ALIAS: case_id},
        invariants=('one writer',),
        non_goals=('publishing',),
        tickets=(record, page, docs),
    )


def add_tickets(draft: PlanDraft, *tickets: TicketDraft) -> PlanDraft:
    return replace(draft, tickets=(*draft.tickets, *tickets))


def replace_ticket(draft: PlanDraft, index: int, ticket: TicketDraft) -> PlanDraft:
    tickets = (*draft.tickets[:index], ticket, *draft.tickets[index + 1 :])
    return replace(draft, tickets=tickets)


def plant_groundless(draft: PlanDraft, index: int) -> PlanDraft:
    ticket = draft.tickets[index]
    first = replace(ticket.acceptance[0], required_by=())
    return replace_ticket(draft, index, replace(ticket, acceptance=(first, *ticket.acceptance[1:])))


def plant_cycle(draft: PlanDraft) -> PlanDraft:
    first, second = LOOP
    looped = (
        replace(create_ticket_draft(first, WORKTREES[0], ('core/loop/a',)), depends_on=(second,)),
        replace(create_ticket_draft(second, WORKTREES[0], ('core/loop/b',)), depends_on=(first,)),
    )
    return add_tickets(draft, *looped)


def plant_collision(draft: PlanDraft, index: int) -> PlanDraft:
    owned = draft.tickets[index].owns[-1]
    return add_tickets(draft, create_ticket_draft(INTRUDER, ROGUE_WORKTREE, (owned,)))


def stamp_plan(draft: PlanDraft, revision: int = 1) -> Plan:
    return RevisionStamp(revision=revision, at=MOMENT, head=HEAD).apply(draft)


def create_plan_document(plan: Plan, previous: Plan | None = None) -> Document:
    changes = PlanChanges(plan=plan, previous=previous)
    return PlanPage(index=PLAN_INDEX, cases={ALIAS: create_case()}, changes=changes).compose()
