"""A small ticket for the plan page writer tests."""

from red_thread_core.documents import CodeListing, parse_line
from red_thread_plans.nodes import Promise, TicketNode


def create_ticket_node(
    title: str = 'draw the `plan`', source: str = 'draw(plan) -> Path'
) -> TicketNode:
    return TicketNode(
        id='plan-page',
        title=parse_line(title),
        lane='core',
        position=2,
        status='changed',
        acceptance=(Promise(text=parse_line('the page renders'), rests_on=('e1', 'e2')),),
        owns=('core/pages/*.py',),
        depends_on=('plan-record',),
        interface=CodeListing(language='python', source=source),
    )
