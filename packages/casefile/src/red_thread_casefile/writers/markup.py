"""HTML for the case file's own nodes: a finding with its verdict, citation, notes and diagram."""

from typing import TYPE_CHECKING

from red_thread_core.elements import element
from red_thread_core.writers.markup import write_finding_id_button, write_line

if TYPE_CHECKING:
    from collections.abc import Sequence

    from red_thread_core.elements import Element

    from red_thread_casefile.documents import CitationNode, FindingNode, Note
    from red_thread_casefile.policy import CitationCheck

STATE_TITLE = 'The citation at the last check'


def describe_citation_state(citation_check: CitationCheck) -> str:
    if citation_check.state != 'moved' or citation_check.moved_to is None:
        return citation_check.state
    return f'moved to line {citation_check.moved_to}'


def write_citation_state_badge(citation_check: CitationCheck | None) -> Element | None:
    if not citation_check:
        return None
    attributes = {'class': 'state', 'data-state': citation_check.state, 'title': STATE_TITLE}
    return (
        element('span')
        .with_attributes(attributes)
        .set_text(describe_citation_state(citation_check))
    )


def write_copy_button(target: str) -> Element:
    attributes = {'type': 'button', 'class': 'copy', 'data-copy': target}
    return element('button').with_attributes(attributes).set_text('Copy')


def write_citation_target(citation_node: CitationNode) -> Element:
    if citation_node.is_url:
        attributes = {'href': citation_node.target, 'rel': 'noreferrer'}
        return element('a').with_attributes(attributes).set_text(citation_node.target)
    return element('code').set_text(citation_node.target)


def write_quoted_lines(quote: str | None) -> Element | None:
    if quote is None:
        return None
    return element('pre').with_attributes({'class': 'quote'}).nest(element('code').set_text(quote))


def write_citation(citation_node: CitationNode | None) -> tuple[Element | None, ...]:
    if citation_node is None:
        return ()
    target = write_citation_target(citation_node)
    citation = element('p').with_attributes({'class': 'citation'})
    line = citation.nest(
        target,
        write_citation_state_badge(citation_node.citation_check),
        write_copy_button(citation_node.target),
    )
    if citation_node.is_url:
        return (line,)
    return (line, write_quoted_lines(citation_node.quote))


def write_flag(flag: str) -> Element:
    return element('li').with_attributes({'class': 'flag'}).set_text(flag)


def write_note(note: Note) -> Element:
    return element('li').set_text(note.text)


def write_notes(finding: FindingNode) -> Element:
    round_stamp = (
        element('li').with_attributes({'class': 'stamp'}).set_text(f'round {finding.round}')
    )
    written_day = finding.at.isoformat()
    time_element = element('time').with_attributes({'datetime': written_day}).set_text(written_day)
    day = element('li').with_attributes({'class': 'stamp'}).nest(time_element)
    flags = map(write_flag, finding.flags)
    notes = map(write_note, finding.notes)
    return element('ul').with_attributes({'class': 'notes'}).nest(round_stamp, day, *flags, *notes)


def write_diagram(diagram: str | None) -> Element | None:
    if diagram is None:
        return None
    return element('pre').with_attributes({'class': 'mermaid'}).set_text(diagram)


def write_claim(finding: FindingNode) -> Element:
    claim = element('p').with_attributes({'class': 'claim'})
    line = write_line(finding.claim)
    if not finding.verdict:
        return claim.nest(*line)
    attributes = {'class': 'verdict', 'data-verdict': finding.verdict}
    badge = element('span').with_attributes(attributes).set_text(finding.verdict)
    return claim.nest(badge, ' ', *line)


def write_finding(finding: FindingNode) -> Element:
    body = element('div').nest(
        write_claim(finding),
        *write_citation(finding.citation_node),
        write_notes(finding),
        write_diagram(finding.diagram),
    )
    attributes = {
        'class': 'finding',
        'id': finding.finding_id,
        'data-kind': finding.kind,
        'data-thread': finding.thread or '',
    }
    return (
        element('li')
        .with_attributes(attributes)
        .nest(write_finding_id_button(finding.finding_id), body)
    )


def write_findings(findings: Sequence[FindingNode]) -> Element | None:
    if not findings:
        return None
    return element('ol').with_attributes({'class': 'thread'}).nest(*map(write_finding, findings))
