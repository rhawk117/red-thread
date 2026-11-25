"""Entry nodes and sections for the document tree tests."""

from red_thread_casefile.documents import EntryList, EntryNode, Section, parse_line


def create_entry_node(ref: str = 'e1', *, lead: str | None = None) -> EntryNode:
    return EntryNode(ref=ref, kind='known', claim=parse_line(f'claim {ref}'), lead=lead)


def create_entry_section(*refs: str, title: str = 'Known') -> Section:
    entries = tuple(map(create_entry_node, refs))
    return Section(title=title, blocks=(EntryList(entries=entries),), kind='known')
