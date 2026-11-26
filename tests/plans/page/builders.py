"""A small ticket for the plan page writer tests."""

from red_thread_core.documents import CodeListing, parse_line
from red_thread_core.places import link_board
from red_thread_plans.nodes import FieldChange, Ground, Promise, TicketNode

BOARD_CASE = '20261121-retry-queue-slowdown'
FOUND = Ground(
    ref='C1.e1',
    kind='decision',
    claim=parse_line('pages open in a browser'),
    url=link_board(BOARD_CASE, 'e1'),
)
LOST = Ground(ref='C1.e9', kind=None, claim=parse_line('This entry is no longer in the case.'))
RETITLED = FieldChange(field='title', removed=('draw it',), added=('draw the plan',))


def create_ticket_node(
    title: str = 'draw the `plan`', source: str = 'draw(plan) -> Path'
) -> TicketNode:
    return TicketNode(
        id='plan-page',
        title=parse_line(title),
        why=parse_line('the owner reads the plan in a browser'),
        worktree='core',
        position=2,
        status='changed',
        acceptance=(Promise(criterion=parse_line('the page renders'), grounds=(FOUND, LOST)),),
        owns=('core/pages/*.py',),
        depends_on=('plan-record',),
        interface=CodeListing(language='python', source=source),
        changes=(RETITLED,),
    )
