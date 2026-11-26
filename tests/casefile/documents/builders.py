"""Entry nodes and sections for the document tree tests."""

from red_thread_casefile.documents import EntryList, EntryNode
from red_thread_core.documents import Section, parse_line

MOMENT = '2026-11-21T10:00:00Z'


def create_entry_node(ref: str = 'e1', *, lead: str | None = None) -> EntryNode:
    claim = parse_line(f'claim {ref}')
    return EntryNode(ref=ref, kind='known', claim=claim, round=1, at=MOMENT, lead=lead)


def create_entry_section(*refs: str, title: str = 'Known') -> Section:
    entries = tuple(map(create_entry_node, refs))
    return Section(title=title, blocks=(EntryList(entries=entries),), kind='known')
