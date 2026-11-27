"""The filters a case file page offers: its findings by kind and by thread."""

from collections import Counter
from typing import TYPE_CHECKING

from red_thread_core.writers.page import Chip, HtmlPage

from red_thread_casefile.charts import MAIN_LEDGER
from red_thread_casefile.documents import list_document_findings

if TYPE_CHECKING:
    from collections.abc import Sequence

    from red_thread_core.documents import Document
    from red_thread_core.writers.page import ChipRow

    from red_thread_casefile.documents import FindingNode
    from red_thread_casefile.views import Heading


def order_name(name: str) -> tuple[int, str]:
    return (len(name), name)


def name_thread(finding: FindingNode) -> str:
    return finding.thread or ''


def list_kind_chips(findings: Sequence[FindingNode], headings: Sequence[Heading]) -> ChipRow:
    counted = Counter(finding.kind for finding in findings)
    return tuple(
        Chip(group='kind', value=heading.kind, label=heading.title, count=counted[heading.kind])
        for heading in headings
        if counted[heading.kind]
    )


def list_thread_chips(findings: Sequence[FindingNode]) -> ChipRow:
    counted = Counter(map(name_thread, findings))
    return tuple(
        Chip(group='thread', value=name, label=name or MAIN_LEDGER, count=counted[name])
        for name in sorted(counted, key=order_name)
    )


def list_finding_filters(document: Document, headings: Sequence[Heading]) -> tuple[ChipRow, ...]:
    findings = list_document_findings(document)
    return (list_kind_chips(findings, headings), list_thread_chips(findings))


def render_case_page(document: Document, headings: Sequence[Heading]) -> str:
    filters = list_finding_filters(document, headings)
    return HtmlPage(document=document, filters=filters).render()
