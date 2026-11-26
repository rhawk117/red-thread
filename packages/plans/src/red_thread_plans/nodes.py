"""The plan's own nodes in the document tree: a ticket, its criteria and grounds, and changes."""

from dataclasses import dataclass
from itertools import chain
from typing import TYPE_CHECKING, Literal

from red_thread_plans.writers import (
    write_change_list,
    write_markdown_changes,
    write_markdown_ticket,
    write_tickets,
)

if TYPE_CHECKING:
    from string.templatelib import Template

    from red_thread_core.documents import CodeListing, Line

type TicketStatus = Literal['new', 'changed', 'unchanged']

TICKET_STATUSES: tuple[TicketStatus, ...] = ('new', 'changed', 'unchanged')


@dataclass(slots=True, kw_only=True, frozen=True)
class Ground:
    ref: str
    kind: str | None
    claim: Line
    url: str | None = None


@dataclass(slots=True, kw_only=True, frozen=True)
class Promise:
    criterion: Line
    grounds: tuple[Ground, ...]

    @property
    def required_by(self) -> tuple[str, ...]:
        return tuple(ground.ref for ground in self.grounds)


@dataclass(slots=True, kw_only=True, frozen=True)
class FieldChange:
    field: str
    removed: tuple[str, ...]
    added: tuple[str, ...]


@dataclass(slots=True, kw_only=True, frozen=True)
class TicketNode:
    id: str
    title: Line
    why: Line
    worktree: str
    position: int
    status: TicketStatus
    acceptance: tuple[Promise, ...] = ()
    owns: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    interface: CodeListing | None = None
    changes: tuple[FieldChange, ...] = ()
    issue: str | None = None


@dataclass(slots=True, kw_only=True, frozen=True)
class TicketList:
    tickets: tuple[TicketNode, ...]
    count: int = 0

    def write_html(self) -> Template:
        return write_tickets(self.tickets)

    def write_markdown(self) -> tuple[str, ...]:
        return tuple(chain.from_iterable(map(write_markdown_ticket, self.tickets)))


@dataclass(slots=True, kw_only=True, frozen=True)
class ChangeList:
    changes: tuple[FieldChange, ...]
    count: int = 0

    def write_html(self) -> Template:
        return write_change_list(self.changes)

    def write_markdown(self) -> tuple[str, ...]:
        return write_markdown_changes(self.changes)
