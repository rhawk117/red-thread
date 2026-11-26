"""The plan's own nodes in the document tree: a ticket with its promises and its status mark."""

from dataclasses import dataclass
from itertools import chain
from typing import TYPE_CHECKING, Literal

from red_thread_casefile.plans.writers import write_markdown_ticket, write_tickets

if TYPE_CHECKING:
    from string.templatelib import Template

    from red_thread_core.documents import CodeListing, Line

type TicketStatus = Literal['new', 'changed', 'unchanged']

TICKET_STATUSES: tuple[TicketStatus, ...] = ('new', 'changed', 'unchanged')


@dataclass(slots=True, kw_only=True, frozen=True)
class Promise:
    text: Line
    rests_on: tuple[str, ...]


@dataclass(slots=True, kw_only=True, frozen=True)
class TicketNode:
    id: str
    title: Line
    lane: str
    position: int
    status: TicketStatus
    acceptance: tuple[Promise, ...] = ()
    owns: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    interface: CodeListing | None = None


@dataclass(slots=True, kw_only=True, frozen=True)
class TicketList:
    tickets: tuple[TicketNode, ...]
    count: int = 0

    def write_html(self) -> Template:
        return write_tickets(self.tickets)

    def write_markdown(self) -> tuple[str, ...]:
        return tuple(chain.from_iterable(map(write_markdown_ticket, self.tickets)))
