"""The filters a case file page offers: its entries by kind and by thread."""

from collections import Counter
from typing import TYPE_CHECKING

from red_thread_core.writers.page import Chip, HtmlPage

from red_thread_casefile.charts import MAIN_LEDGER
from red_thread_casefile.documents import list_document_entries
from red_thread_casefile.views import HEADINGS

if TYPE_CHECKING:
    from red_thread_core.documents import Document
    from red_thread_core.writers.page import ChipRow

    from red_thread_casefile.documents import EntryNode


def order_name(name: str) -> tuple[int, str]:
    return (len(name), name)


def name_thread(entry: EntryNode) -> str:
    return entry.thread or ''


def list_kind_chips(entries: tuple[EntryNode, ...]) -> ChipRow:
    counted = Counter(entry.kind for entry in entries)
    return tuple(
        Chip(group='kind', value=heading.kind, label=heading.title, count=counted[heading.kind])
        for heading in HEADINGS
        if counted[heading.kind]
    )


def list_thread_chips(entries: tuple[EntryNode, ...]) -> ChipRow:
    counted = Counter(map(name_thread, entries))
    return tuple(
        Chip(group='thread', value=name, label=name or MAIN_LEDGER, count=counted[name])
        for name in sorted(counted, key=order_name)
    )


def list_entry_filters(document: Document) -> tuple[ChipRow, ...]:
    entries = list_document_entries(document)
    return (list_kind_chips(entries), list_thread_chips(entries))


def render_case_page(document: Document) -> str:
    return HtmlPage(document=document, filters=list_entry_filters(document)).render()
