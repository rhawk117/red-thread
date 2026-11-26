"""HTML and Markdown for the plan's own nodes: a ticket, its criteria and grounds, and changes."""

from typing import TYPE_CHECKING

from red_thread_core.writers.markdown import write_markdown_line
from red_thread_core.writers.markup import write_line, write_listing, write_ref

if TYPE_CHECKING:
    from string.templatelib import Template

    from red_thread_plans.nodes import FieldChange, Ground, Promise, TicketNode

NOT_PUBLISHED = 'not published yet'
MISSING_KIND = 'missing'
DIFF_TITLE = 'What changed since the revision before'
NOTHING = 'nothing'


def write_issue(ticket: TicketNode) -> Template:
    if ticket.issue is None:
        return t'<li>issue {NOT_PUBLISHED}</li>'
    return t'<li><a href="{ticket.issue}" rel="noreferrer">issue</a></li>'


def write_ticket_notes(ticket: TicketNode) -> Template:
    place = t'<li class="stamp">worktree {ticket.worktree}, position {ticket.position}</li>'
    after = ', '.join(ticket.depends_on)
    depends = t'<li>depends on: {after}</li>' if after else t''
    owned = tuple(t'<li><code>{owned}</code></li>' for owned in ticket.owns)
    return t'<ul class="notes">{place}{depends}{write_issue(ticket)}{owned}</ul>'


def write_ground_ref(ground: Ground) -> Template:
    if ground.url is None:
        return t'<span class="ground-ref">{ground.ref}</span>'
    return t'<a class="ground-ref" href="{ground.url}">{ground.ref}</a>'


def write_ground(ground: Ground) -> Template:
    kind = ground.kind or MISSING_KIND
    label = t'<span class="ground-kind">{kind}</span>'
    text = t'<span class="ground-text">{write_line(ground.claim)}</span>'
    return t'<li class="ground" data-kind="{kind}">{write_ground_ref(ground)}{label}{text}</li>'


def write_promise(promise: Promise) -> Template:
    criterion = t'<p class="criterion">{write_line(promise.criterion)}</p>'
    grounds = t'<ul class="grounds">{tuple(map(write_ground, promise.grounds))}</ul>'
    return t'<li>{criterion}{grounds}</li>'


def write_change(change: FieldChange) -> Template:
    removed = tuple(t'<del>{value}</del>' for value in change.removed)
    added = tuple(t'<ins>{value}</ins>' for value in change.added)
    return t'<div><dt>{change.field}</dt><dd>{removed}{added}</dd></div>'


def write_change_list(changes: tuple[FieldChange, ...]) -> Template:
    if not changes:
        return t''
    return t'<dl class="changes">{tuple(map(write_change, changes))}</dl>'


def write_ticket_changes(ticket: TicketNode) -> Template:
    if not ticket.changes:
        return t''
    heading = t'<summary>{DIFF_TITLE}</summary>'
    return t'<details class="diff">{heading}{write_change_list(ticket.changes)}</details>'


def write_ticket(ticket: TicketNode) -> Template:
    mark = t'<span class="status" data-status="{ticket.status}">{ticket.status}</span>'
    claim = t'<p class="claim">{mark} {write_line(ticket.title)}</p>'
    why = t'<p class="why">{write_line(ticket.why)}</p>'
    listed = t'<ol class="promises">{tuple(map(write_promise, ticket.acceptance))}</ol>'
    done = t'<p class="label">Done when</p>{listed}'
    extra = t'{write_ticket_changes(ticket)}{write_listing(ticket.interface)}'
    body = t'<div>{claim}{why}{write_ticket_notes(ticket)}{done}{extra}</div>'
    marks = t'data-worktree="{ticket.worktree}" data-status="{ticket.status}"'
    return t'<li class="entry ticket" id="{ticket.id}" {marks}>{write_ref(ticket.id)}{body}</li>'


def write_tickets(tickets: tuple[TicketNode, ...]) -> Template:
    if not tickets:
        return t''
    return t'<ol class="thread">{tuple(map(write_ticket, tickets))}</ol>'


def list_refs(promise: Promise) -> str:
    return ', '.join(promise.required_by)


def describe_change(change: FieldChange) -> str:
    removed = '; '.join(change.removed) or NOTHING
    added = '; '.join(change.added) or NOTHING
    return f'{change.field}: {removed} -> {added}'


def write_markdown_changes(changes: tuple[FieldChange, ...]) -> tuple[str, ...]:
    return tuple(f'- {describe_change(change)}' for change in changes)


def write_markdown_ticket(ticket: TicketNode) -> tuple[str, ...]:
    title = write_markdown_line(ticket.title)
    place = f'{ticket.status}; worktree {ticket.worktree}, position {ticket.position}'
    promises = (
        f'  - {write_markdown_line(promise.criterion)} (required by {list_refs(promise)})'
        for promise in ticket.acceptance
    )
    why = f'  Why: {write_markdown_line(ticket.why)}'
    changed = (f'  Changed {describe_change(change)}' for change in ticket.changes)
    return (f'- {title} ({place}) [{ticket.id}]', why, *promises, *changed)
