"""A ledger to rest a plan on, a plan that passes every check and the faults planted in one."""

from typing import TYPE_CHECKING

from msgspec.structs import replace
from red_thread_casefile.domain import Ledger
from red_thread_casefile.plans.domain import Acceptance, PlanDraft, TicketDraft
from red_thread_casefile.plans.page import PlanChanges, PlanPage
from red_thread_casefile.plans.policy import create_grounds
from red_thread_casefile.services.planning import RevisionStamp

from tests.casefile.ledger.builders import URL_CITE, create_case, create_entry
from tests.casefile.ledger.memory import HEAD, MOMENT

if TYPE_CHECKING:
    from red_thread_casefile.plans.domain import Plan
    from red_thread_casefile.plans.policy import Grounds
    from red_thread_core.documents import Document

LANES = ('core', 'docs', 'web')
RESTING_REFS = ('e1', 'e2')
OPEN_REF = 'e3'
RETIRED_REF = 'e4'
UNKNOWN_REF = 'e99'
LOOP = ('loop-a', 'loop-b')
INTRUDER = 'intruder'
ROGUE_LANE = 'rogue'


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
    return create_grounds(create_resting_ledger())


def create_ticket_draft(ticket_id: str, lane: str, owns: tuple[str, ...]) -> TicketDraft:
    return TicketDraft(
        id=ticket_id,
        title=f'build {ticket_id}',
        lane=lane,
        acceptance=(Acceptance(text=f'{ticket_id} holds', rests_on=RESTING_REFS),),
        owns=owns,
    )


def create_valid_draft() -> PlanDraft:
    record = create_ticket_draft('plan-record', 'core', ('core/plans/',))
    page = replace(
        create_ticket_draft('plan-page', 'core', ('core/pages/*.py',)),
        depends_on=('plan-record',),
    )
    docs = create_ticket_draft('docs', 'docs', ('docs/**/*.md',))
    return PlanDraft(
        intent='give a case a plan',
        approach='store it beside the ledger',
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
    first = replace(ticket.acceptance[0], rests_on=())
    return replace_ticket(draft, index, replace(ticket, acceptance=(first, *ticket.acceptance[1:])))


def plant_cycle(draft: PlanDraft) -> PlanDraft:
    first, second = LOOP
    looped = (
        replace(create_ticket_draft(first, LANES[0], ('core/loop/a',)), depends_on=(second,)),
        replace(create_ticket_draft(second, LANES[0], ('core/loop/b',)), depends_on=(first,)),
    )
    return add_tickets(draft, *looped)


def plant_collision(draft: PlanDraft, index: int) -> PlanDraft:
    owned = draft.tickets[index].owns[-1]
    return add_tickets(draft, create_ticket_draft(INTRUDER, ROGUE_LANE, (owned,)))


def stamp_plan(draft: PlanDraft, revision: int = 1) -> Plan:
    return RevisionStamp(revision=revision, at=MOMENT, head=HEAD).apply(draft)


def create_plan_document(plan: Plan, previous: Plan | None = None) -> Document:
    changes = PlanChanges(plan=plan, previous=previous)
    return PlanPage(case=create_case(), changes=changes).compose()
