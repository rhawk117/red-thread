"""Markdown for the case file's own nodes: a finding with its remarks, citation and finding id."""

from typing import TYPE_CHECKING

from red_thread_core.writers.markdown import write_markdown_line

from red_thread_casefile.views import list_citation_flags

if TYPE_CHECKING:
    from red_thread_casefile.documents import CitationNode, FindingNode


def write_citation(citation_node: CitationNode | None) -> str:
    if citation_node is None:
        return ''

    if citation_node.is_url:
        return f' <{citation_node.target}>'

    return f' `{citation_node.target}`'


def write_markdown_finding(finding: FindingNode) -> str:
    citation_check = finding.citation_node.citation_check if finding.citation_node else None
    notes = (note.text for note in finding.notes)
    remarks = '; '.join((*finding.flags, *list_citation_flags(citation_check), *notes))
    noted = f' ({remarks})' if remarks else ''
    citation = write_citation(finding.citation_node)
    return f'- {write_markdown_line(finding.claim)}{noted}{citation} [{finding.finding_id}]'
