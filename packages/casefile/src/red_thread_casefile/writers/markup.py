"""HTML from the document tree: every value escaped by one function, every node one fragment."""

from dataclasses import dataclass, field
from html import escape
from string.templatelib import Interpolation, Template, convert
from typing import TYPE_CHECKING

from red_thread_casefile.domain import date_of

if TYPE_CHECKING:
    from red_thread_casefile.documents import (
        Block,
        Citation,
        Code,
        CodeListing,
        EntryList,
        EntryNode,
        Fact,
        Flowchart,
        Inline,
        Line,
        Link,
        Paragraph,
        PointList,
        Section,
        Text,
    )
    from red_thread_casefile.plans.nodes import Promise, TicketList, TicketNode
    from red_thread_casefile.policy import Finding

STATE_TITLE = 'The citation at the last check'


def render_value(value: object) -> str:
    if isinstance(value, Template):
        return render(value)
    if isinstance(value, tuple):
        return ''.join(map(render_value, value))
    return escape(str(value))


def render_part(part: str | Interpolation[object]) -> str:
    if isinstance(part, Interpolation):
        return render_value(convert(part.value, part.conversion))
    return part


def render(template: Template) -> str:
    return ''.join(map(render_part, template))


def label_state(finding: Finding) -> str:
    if finding.state != 'moved' or finding.moved_to is None:
        return finding.state
    return f'moved to line {finding.moved_to}'


def write_state(finding: Finding | None) -> Template:
    if not finding:
        return t''
    marks = t'class="state" data-state="{finding.state}" title="{STATE_TITLE}"'
    return t'<span {marks}>{label_state(finding)}</span>'


def write_cite(citation: Citation | None) -> Template:
    if citation is None:
        return t''
    target = citation.target
    copy = t'<button type="button" class="copy" data-copy="{target}">Copy</button>'
    tools = t'{write_state(citation.finding)}{copy}'
    if citation.is_url:
        return t'<p class="cite"><a href="{target}" rel="noreferrer">{target}</a>{tools}</p>'
    quote = citation.quote
    shown = t'<pre class="quote"><code>{quote}</code></pre>' if quote is not None else t''
    return t'<p class="cite"><code>{target}</code>{tools}</p>{shown}'


def write_ref(ref: str) -> Template:
    return t'<button type="button" class="ref" data-copy="{ref}" title="Copy">{ref}</button>'


def write_notes(entry: EntryNode) -> Template:
    round_stamp = t'<li class="stamp">round {entry.round}</li>'
    day = t'<li class="stamp"><time datetime="{entry.at}">{date_of(entry.at)}</time></li>'
    flags = tuple(t'<li class="flag">{flag}</li>' for flag in entry.flags)
    notes = tuple(t'<li>{note.text}</li>' for note in entry.notes)
    return t'<ul class="notes">{round_stamp}{day}{flags}{notes}</ul>'


def write_diagram(diagram: str | None) -> Template:
    if diagram is None:
        return t''
    return t'<pre class="mermaid">{diagram}</pre>'


def write_fold(section: Section, body: Template) -> Template:
    entries = section.entries
    count = t'<span class="count">{len(entries)}</span>' if entries else t''
    note = t'<span class="about">{section.note}</span>' if section.note else t''
    kind = t' data-kind="{section.kind}"' if section.kind else t''
    state = t'' if section.folded else t' open'
    heading = t'<summary><h2>{section.title}</h2>{count}{note}</summary>'
    return t'<details class="section"{kind}{state}>\n{heading}\n{body}\n</details>\n'


@dataclass(slots=True, kw_only=True, frozen=True)
class HtmlInlines:
    def write_text(self, node: Text) -> Template:
        return t'{node.value}'

    def write_code(self, node: Code) -> Template:
        return t'<code>{node.value}</code>'

    def write_link(self, node: Link) -> Template:
        return t'<a href="{node.url}" rel="noreferrer">{node.url}</a>'

    def write_inline(self, node: Inline) -> Template:
        return node.write(self)

    def write_line(self, line: Line) -> Template:
        return t'{tuple(map(self.write_inline, line))}'


def write_claim(inlines: HtmlInlines, entry: EntryNode) -> Template:
    line = inlines.write_line(entry.claim)
    if not entry.verdict:
        return t'<p class="claim">{line}</p>'
    badge = t'<span class="verdict" data-verdict="{entry.verdict}">{entry.verdict}</span>'
    return t'<p class="claim">{badge} {line}</p>'


def write_point(inlines: HtmlInlines, point: Line) -> Template:
    claim = t'<p class="claim">{inlines.write_line(point)}</p>'
    return t'<li class="entry"><div>{claim}</div></li>'


def write_listing(listing: CodeListing | None) -> Template:
    if listing is None:
        return t''
    code = t'<code>{listing.source}</code>'
    return t'<pre class="listing" data-language="{listing.language}">{code}</pre>'


def write_ticket_notes(ticket: TicketNode) -> Template:
    place = t'<li class="stamp">lane {ticket.lane}, position {ticket.position}</li>'
    after = ', '.join(ticket.depends_on)
    depends = t'<li>depends on: {after}</li>' if after else t''
    owned = tuple(t'<li><code>{owned}</code></li>' for owned in ticket.owns)
    return t'<ul class="notes">{place}{depends}{owned}</ul>'


@dataclass(slots=True, kw_only=True, frozen=True)
class HtmlTickets:
    inlines: HtmlInlines = field(default_factory=HtmlInlines)

    def write_promise(self, promise: Promise) -> Template:
        rests = t'<span class="rests">rests on {", ".join(promise.rests_on)}</span>'
        return t'<li>{self.inlines.write_line(promise.text)} {rests}</li>'

    def write_ticket(self, ticket: TicketNode) -> Template:
        mark = t'<span class="status" data-status="{ticket.status}">{ticket.status}</span>'
        claim = t'<p class="claim">{mark} {self.inlines.write_line(ticket.title)}</p>'
        promises = tuple(map(self.write_promise, ticket.acceptance))
        listed = t'<ol class="promises">{promises}</ol>'
        details = t'{write_ticket_notes(ticket)}{listed}{write_listing(ticket.interface)}'
        body = t'<div>{claim}{details}</div>'
        marks = t'data-lane="{ticket.lane}" data-status="{ticket.status}"'
        return t'<li class="entry ticket" {marks}>{write_ref(ticket.id)}{body}</li>'

    def write_tickets(self, node: TicketList) -> Template:
        if not node.tickets:
            return t''
        return t'<ol class="thread">{tuple(map(self.write_ticket, node.tickets))}</ol>'


@dataclass(slots=True, kw_only=True, frozen=True)
class HtmlWriter:
    inlines: HtmlInlines = field(default_factory=HtmlInlines)
    tickets: HtmlTickets = field(default_factory=HtmlTickets)

    def write_entry(self, entry: EntryNode) -> Template:
        details = t'{write_cite(entry.citation)}{write_notes(entry)}{write_diagram(entry.diagram)}'
        body = t'<div>{write_claim(self.inlines, entry)}{details}</div>'
        marks = t'data-kind="{entry.kind}" data-thread="{entry.thread or ""}"'
        return t'<li class="entry" {marks}>{write_ref(entry.ref)}{body}</li>'

    def write_paragraph(self, node: Paragraph) -> Template:
        return t'<p>{self.inlines.write_line(node.line)}</p>'

    def write_entries(self, node: EntryList) -> Template:
        if not node.entries:
            return t''
        return t'<ol class="thread">{tuple(map(self.write_entry, node.entries))}</ol>'

    def write_points(self, node: PointList) -> Template:
        if not node.points:
            return t''
        points = tuple(write_point(self.inlines, point) for point in node.points)
        return t'<ol class="plain">{points}</ol>'

    def write_flowchart(self, node: Flowchart) -> Template:
        return t'<pre class="mermaid">{"\n".join(node.lines)}</pre>'

    def write_listing(self, node: CodeListing) -> Template:
        return write_listing(node)

    def write_tickets(self, node: TicketList) -> Template:
        return self.tickets.write_tickets(node)

    def write_block(self, block: Block) -> Template:
        return block.write(self)

    def write_section(self, section: Section) -> Template:
        return write_fold(section, t'{tuple(map(self.write_block, section.blocks))}')

    def write_fact(self, fact: Fact) -> Template:
        style = 'fact wide' if fact.wide else 'fact'
        value = self.inlines.write_line(fact.value)
        return t'<div class="{style}"><dt>{fact.label}</dt><dd>{value}</dd></div>'
