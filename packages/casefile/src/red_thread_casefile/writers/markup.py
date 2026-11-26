"""HTML for the case file's own nodes: an entry with its verdict, citation, notes and diagram."""

from typing import TYPE_CHECKING

from red_thread_core.writers.markup import write_line, write_ref

from red_thread_casefile.domain import date_of

if TYPE_CHECKING:
    from string.templatelib import Template

    from red_thread_casefile.documents import Citation, EntryNode
    from red_thread_casefile.policy import Finding

STATE_TITLE = 'The citation at the last check'


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


def write_claim(entry: EntryNode) -> Template:
    line = write_line(entry.claim)
    if not entry.verdict:
        return t'<p class="claim">{line}</p>'
    badge = t'<span class="verdict" data-verdict="{entry.verdict}">{entry.verdict}</span>'
    return t'<p class="claim">{badge} {line}</p>'


def write_entry(entry: EntryNode) -> Template:
    details = t'{write_cite(entry.citation)}{write_notes(entry)}{write_diagram(entry.diagram)}'
    body = t'<div>{write_claim(entry)}{details}</div>'
    marks = t'data-kind="{entry.kind}" data-thread="{entry.thread or ""}"'
    return t'<li class="entry" {marks}>{write_ref(entry.ref)}{body}</li>'


def write_entries(entries: tuple[EntryNode, ...]) -> Template:
    if not entries:
        return t''
    return t'<ol class="thread">{tuple(map(write_entry, entries))}</ol>'
