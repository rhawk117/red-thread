"""Small documents for the writer tests."""

from red_thread_casefile.documents import FindingList, FindingNode
from red_thread_core.documents import Document, Paragraph, Section, parse_line

from tests.core.timekeeping.clock import DAY


def create_finding_node(text: str = 'a claim', finding_id: str = 'e1') -> FindingNode:
    return FindingNode(finding_id=finding_id, kind='known', claim=parse_line(text), round=1, at=DAY)


def create_document(
    *findings: FindingNode, title: str = 'A case', prose: tuple[str, ...] = ()
) -> Document:
    paragraphs = tuple(Paragraph(line=parse_line(line)) for line in prose)
    listing = (FindingList(findings=findings),) if findings else ()
    section = Section(title='Findings', blocks=(*paragraphs, *listing))
    return Document(title=title, summary=(parse_line('Case summary line'),), sections=(section,))
