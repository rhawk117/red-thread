"""The case file page: its filters by entry kind and by thread, drawn with the entry templates."""

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_core.writers.markup import create_page_environment
from red_thread_core.writers.page import Chip, HtmlPage, PageWriter

from red_thread_casefile.charts import MAIN_LEDGER
from red_thread_casefile.documents import list_document_entries
from red_thread_casefile.domain import date_of
from red_thread_casefile.packaged import CASEFILE_PACKAGE

if TYPE_CHECKING:
    from red_thread_core.documents import Document
    from red_thread_core.writers.page import ChipRow

    from red_thread_casefile.documents import EntryNode
    from red_thread_casefile.policy import Finding
    from red_thread_casefile.views import Heading


def label_state(finding: Finding) -> str:
    if finding.state != 'moved' or finding.moved_to is None:
        return finding.state
    return f'moved to line {finding.moved_to}'


def order_name(name: str) -> tuple[int, str]:
    return (len(name), name)


def name_thread(entry: EntryNode) -> str:
    return entry.thread or ''


def list_kind_chips(entries: tuple[EntryNode, ...], headings: tuple[Heading, ...]) -> ChipRow:
    counted = Counter(entry.kind for entry in entries)
    return tuple(
        Chip(group='kind', value=heading.kind, label=heading.title, count=counted[heading.kind])
        for heading in headings
        if counted[heading.kind]
    )


def list_thread_chips(entries: tuple[EntryNode, ...]) -> ChipRow:
    counted = Counter(map(name_thread, entries))
    return tuple(
        Chip(group='thread', value=name, label=name or MAIN_LEDGER, count=counted[name])
        for name in sorted(counted, key=order_name)
    )


def list_entry_filters(document: Document, headings: tuple[Heading, ...]) -> tuple[ChipRow, ...]:
    entries = list_document_entries(document)
    return (list_kind_chips(entries, headings), list_thread_chips(entries))


@dataclass(slots=True, kw_only=True, frozen=True)
class CasePageWriter:
    writer: PageWriter
    headings: tuple[Heading, ...]

    def render(self, document: Document) -> str:
        filters = list_entry_filters(document, self.headings)
        return self.writer.render(HtmlPage(document=document, filters=filters))


def create_case_page_writer(headings: tuple[Heading, ...]) -> CasePageWriter:
    environment = create_page_environment(CASEFILE_PACKAGE)
    environment.filters.update(state_label=label_state, date_of=date_of)
    return CasePageWriter(writer=PageWriter(environment=environment), headings=headings)
