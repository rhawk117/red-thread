"""Markdown for the case file's own nodes: an entry with its remarks, citation and ref."""

from typing import TYPE_CHECKING

from red_thread_core.writers.markdown import write_markdown_line

from red_thread_casefile.views import list_cite_flags

if TYPE_CHECKING:
    from red_thread_casefile.documents import Citation, EntryNode


def write_citation(citation: Citation | None) -> str:
    if citation is None:
        return ''

    if citation.is_url:
        return f' <{citation.target}>'

    return f' `{citation.target}`'


def write_markdown_entry(entry: EntryNode) -> str:
    finding = entry.citation.finding if entry.citation else None
    notes = (note.text for note in entry.notes)
    remarks = '; '.join((*entry.flags, *list_cite_flags(finding), *notes))
    noted = f' ({remarks})' if remarks else ''
    cite = write_citation(entry.citation)
    return f'- {write_markdown_line(entry.claim)}{noted}{cite} [{entry.ref}]'
