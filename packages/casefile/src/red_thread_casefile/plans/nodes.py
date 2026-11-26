"""The plan's own nodes in the document tree: a ticket with its promises and its status mark."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from red_thread_casefile.documents import BlockWriter, CodeListing, Line

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

    def write[T](self, writer: BlockWriter[T]) -> T:
        return writer.write_tickets(self)
