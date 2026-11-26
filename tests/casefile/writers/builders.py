"""Small documents for the writer tests."""

from red_thread_casefile.documents import EntryList, EntryNode
from red_thread_core.documents import Document, Paragraph, Section, parse_line

from tests.casefile.documents.builders import MOMENT


def create_entry_node(text: str = 'a claim', ref: str = 'e1') -> EntryNode:
    return EntryNode(ref=ref, kind='known', claim=parse_line(text), round=1, at=MOMENT)


def create_document(
    *entries: EntryNode, title: str = 'A case', prose: tuple[str, ...] = ()
) -> Document:
    paragraphs = tuple(Paragraph(line=parse_line(line)) for line in prose)
    listing = (EntryList(entries=entries),) if entries else ()
    section = Section(title='Findings', blocks=(*paragraphs, *listing))
    return Document(title=title, summary=(parse_line('Case summary line'),), sections=(section,))
