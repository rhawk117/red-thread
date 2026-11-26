"""HTML and Markdown for the plan's own nodes: a ticket with its place, promises and interface."""

from typing import TYPE_CHECKING

from red_thread_core.writers.markdown import write_markdown_line
from red_thread_core.writers.markup import write_line, write_listing, write_ref

if TYPE_CHECKING:
    from string.templatelib import Template

    from red_thread_casefile.plans.nodes import Promise, TicketNode


def write_ticket_notes(ticket: TicketNode) -> Template:
    place = t'<li class="stamp">lane {ticket.lane}, position {ticket.position}</li>'
    after = ', '.join(ticket.depends_on)
    depends = t'<li>depends on: {after}</li>' if after else t''
    owned = tuple(t'<li><code>{owned}</code></li>' for owned in ticket.owns)
    return t'<ul class="notes">{place}{depends}{owned}</ul>'


def write_promise(promise: Promise) -> Template:
    rests = t'<span class="rests">rests on {", ".join(promise.rests_on)}</span>'
    return t'<li>{write_line(promise.text)} {rests}</li>'


def write_ticket(ticket: TicketNode) -> Template:
    mark = t'<span class="status" data-status="{ticket.status}">{ticket.status}</span>'
    claim = t'<p class="claim">{mark} {write_line(ticket.title)}</p>'
    listed = t'<ol class="promises">{tuple(map(write_promise, ticket.acceptance))}</ol>'
    details = t'{write_ticket_notes(ticket)}{listed}{write_listing(ticket.interface)}'
    body = t'<div>{claim}{details}</div>'
    marks = t'data-lane="{ticket.lane}" data-status="{ticket.status}"'
    return t'<li class="entry ticket" {marks}>{write_ref(ticket.id)}{body}</li>'


def write_tickets(tickets: tuple[TicketNode, ...]) -> Template:
    if not tickets:
        return t''
    return t'<ol class="thread">{tuple(map(write_ticket, tickets))}</ol>'


def write_markdown_ticket(ticket: TicketNode) -> tuple[str, ...]:
    title = write_markdown_line(ticket.title)
    place = f'{ticket.status}; lane {ticket.lane}, position {ticket.position}'
    promises = (
        f'  - {write_markdown_line(promise.text)} (rests on {", ".join(promise.rests_on)})'
        for promise in ticket.acceptance
    )
    return (f'- {title} ({place}) [{ticket.id}]', *promises)
