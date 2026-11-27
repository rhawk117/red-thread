"""HTML for the case file's own nodes: an entry with its verdict, citation, notes and diagram."""

from typing import TYPE_CHECKING

from red_thread_core.elements import element
from red_thread_core.writers.markup import write_line, write_ref

from red_thread_casefile.domain import date_of

if TYPE_CHECKING:
    from red_thread_core.elements import Element

    from red_thread_casefile.documents import Citation, EntryNode, Note
    from red_thread_casefile.policy import Finding

STATE_TITLE = 'The citation at the last check'


def label_state(finding: Finding) -> str:
    if finding.state != 'moved' or finding.moved_to is None:
        return finding.state
    return f'moved to line {finding.moved_to}'


def write_state(finding: Finding | None) -> Element | None:
    if not finding:
        return None
    marks = {'class': 'state', 'data-state': finding.state, 'title': STATE_TITLE}
    return element('span').attributes(marks).set_text(label_state(finding))


def write_copy(target: str) -> Element:
    marks = {'type': 'button', 'class': 'copy', 'data-copy': target}
    return element('button').attributes(marks).set_text('Copy')


def write_target(citation: Citation) -> Element:
    if citation.is_url:
        marks = {'href': citation.target, 'rel': 'noreferrer'}
        return element('a').attributes(marks).set_text(citation.target)
    return element('code').set_text(citation.target)


def write_quote(quote: str | None) -> Element | None:
    if quote is None:
        return None
    return element('pre').attributes({'class': 'quote'}).nest(element('code').set_text(quote))


def write_cite(citation: Citation | None) -> tuple[Element | None, ...]:
    if citation is None:
        return ()
    target = write_target(citation)
    cite = element('p').attributes({'class': 'cite'})
    line = cite.nest(target, write_state(citation.finding), write_copy(citation.target))
    if citation.is_url:
        return (line,)
    return (line, write_quote(citation.quote))


def write_flag(flag: str) -> Element:
    return element('li').attributes({'class': 'flag'}).set_text(flag)


def write_note(note: Note) -> Element:
    return element('li').set_text(note.text)


def write_notes(entry: EntryNode) -> Element:
    round_stamp = element('li').attributes({'class': 'stamp'}).set_text(f'round {entry.round}')
    time = element('time').attributes({'datetime': entry.at}).set_text(date_of(entry.at))
    day = element('li').attributes({'class': 'stamp'}).nest(time)
    flags = map(write_flag, entry.flags)
    notes = map(write_note, entry.notes)
    return element('ul').attributes({'class': 'notes'}).nest(round_stamp, day, *flags, *notes)


def write_diagram(diagram: str | None) -> Element | None:
    if diagram is None:
        return None
    return element('pre').attributes({'class': 'mermaid'}).set_text(diagram)


def write_claim(entry: EntryNode) -> Element:
    claim = element('p').attributes({'class': 'claim'})
    line = write_line(entry.claim)
    if not entry.verdict:
        return claim.nest(*line)
    marks = {'class': 'verdict', 'data-verdict': entry.verdict}
    badge = element('span').attributes(marks).set_text(entry.verdict)
    return claim.nest(badge, ' ', *line)


def write_entry(entry: EntryNode) -> Element:
    body = element('div').nest(
        write_claim(entry),
        *write_cite(entry.citation),
        write_notes(entry),
        write_diagram(entry.diagram),
    )
    marks = {
        'class': 'entry',
        'id': entry.ref,
        'data-kind': entry.kind,
        'data-thread': entry.thread or '',
    }
    return element('li').attributes(marks).nest(write_ref(entry.ref), body)


def write_entries(entries: tuple[EntryNode, ...]) -> Element | None:
    if not entries:
        return None
    return element('ol').attributes({'class': 'thread'}).nest(*map(write_entry, entries))
