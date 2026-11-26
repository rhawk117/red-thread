"""The filters a plan page offers: its tickets by lane and by status."""

from collections import Counter
from itertools import chain
from typing import TYPE_CHECKING

from red_thread_core.writers.page import Chip, HtmlPage

from red_thread_casefile.plans.nodes import TICKET_STATUSES, TicketList

if TYPE_CHECKING:
    from red_thread_core.documents import Document
    from red_thread_core.writers.page import ChipRow

    from red_thread_casefile.plans.nodes import TicketNode


def list_tickets(document: Document) -> tuple[TicketNode, ...]:
    blocks = chain.from_iterable(section.blocks for section in document.sections)
    lists = (block.tickets for block in blocks if isinstance(block, TicketList))
    return tuple(chain.from_iterable(lists))


def list_lane_chips(tickets: tuple[TicketNode, ...]) -> ChipRow:
    counted = Counter(ticket.lane for ticket in tickets)
    return tuple(
        Chip(group='lane', value=lane, label=lane, count=counted[lane]) for lane in counted
    )


def list_status_chips(tickets: tuple[TicketNode, ...]) -> ChipRow:
    counted = Counter(ticket.status for ticket in tickets)
    return tuple(
        Chip(group='status', value=status, label=status, count=counted[status])
        for status in TICKET_STATUSES
        if counted[status]
    )


def list_ticket_filters(document: Document) -> tuple[ChipRow, ...]:
    tickets = list_tickets(document)
    return (list_lane_chips(tickets), list_status_chips(tickets))


def render_plan_page(document: Document) -> str:
    return HtmlPage(document=document, filters=list_ticket_filters(document)).render()
