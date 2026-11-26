"""Small documents for the writer tests."""

from red_thread_casefile.documents import (
    CodeListing,
    Document,
    EntryList,
    EntryNode,
    Paragraph,
    Section,
    parse_line,
)
from red_thread_casefile.plans.nodes import Promise, TicketNode

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


def create_ticket_node(
    title: str = 'draw the `plan`', source: str = 'draw(plan) -> Path'
) -> TicketNode:
    return TicketNode(
        id='plan-page',
        title=parse_line(title),
        lane='core',
        position=2,
        status='changed',
        acceptance=(Promise(text=parse_line('the page renders'), rests_on=('e1', 'e2')),),
        owns=('core/pages/*.py',),
        depends_on=('plan-record',),
        interface=CodeListing(language='python', source=source),
    )
