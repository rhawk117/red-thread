"""Finding nodes and sections for the document tree tests."""

from red_thread_casefile.documents import FindingList, FindingNode
from red_thread_core.documents import Section, parse_line

from tests.core.timekeeping.clock import DAY


def create_finding_node(finding_id: str = 'e1', *, lead: str | None = None) -> FindingNode:
    claim = parse_line(f'claim {finding_id}')
    return FindingNode(finding_id=finding_id, kind='known', claim=claim, round=1, at=DAY, lead=lead)


def create_finding_section(*finding_ids: str, title: str = 'Known') -> Section:
    findings = tuple(map(create_finding_node, finding_ids))
    return Section(title=title, blocks=(FindingList(findings=findings),), kind='known')
