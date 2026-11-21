"""Documents for the page and Markdown writers, with one field carrying the text under test."""

from dataclasses import replace
from typing import TYPE_CHECKING, Literal, cast

from red_thread_casefile.views import Document, Item, Section

if TYPE_CHECKING:
    from red_thread_casefile.domain import EntryKind

type DocumentField = Literal[
    'title',
    'summary',
    'section-title',
    'prose',
    'item-text',
    'item-cite',
    'item-url-cite',
    'item-ref',
    'item-note',
    'item-flag',
    'item-kind',
    'item-thread',
    'item-diagram',
    'map-line',
]

DOCUMENT_FIELDS: tuple[DocumentField, ...] = (
    'title',
    'summary',
    'section-title',
    'prose',
    'item-text',
    'item-cite',
    'item-url-cite',
    'item-ref',
    'item-note',
    'item-flag',
    'item-kind',
    'item-thread',
    'item-diagram',
    'map-line',
)
PLAIN_URL = 'https://example.invalid/docs'


def create_marked_item(
    *, ref: str = 'e1', kind: EntryKind | None = 'known', thread: str | None = None
) -> Item:
    return Item(text='a claim', ref=ref, kind=kind, thread=thread)


def create_document(*items: Item, title: str = 'A case', prose: tuple[str, ...] = ()) -> Document:
    section = Section(title='Findings', items=items, prose=prose)
    return Document(title=title, summary=('Case summary line',), sections=(section,))


def create_document_carrying(field: DocumentField, text: str) -> Document:
    item = Item(
        text='plain text',
        ref='e1',
        cite='src/queue.py:3',
        notes=('rests on: plain',),
        flags=('lead, recorded at 1111111',),
        kind='known',
        thread='T1',
    )
    other = Item(text='other text', ref='e2', kind='open')
    base = create_document(item, other)
    section = base.sections[0]
    variants = {
        'title': replace(base, title=text),
        'summary': replace(base, summary=(text,)),
        'section-title': replace(base, sections=(replace(section, title=text),)),
        'prose': replace(base, sections=(replace(section, prose=(text,)),)),
        'item-text': create_document(replace(item, text=text), other),
        'item-cite': create_document(replace(item, cite=text), other),
        'item-url-cite': create_document(replace(item, cite=f'{PLAIN_URL}/{text}'), other),
        'item-ref': create_document(replace(item, ref=text), other),
        'item-note': create_document(replace(item, notes=(text,)), other),
        'item-flag': create_document(replace(item, flags=(text,)), other),
        'item-kind': create_document(replace(item, kind=cast('EntryKind', text)), other),
        'item-thread': create_document(replace(item, thread=text), other),
        'item-diagram': create_document(replace(item, diagram=text), other),
        'map-line': replace(base, map_lines=(text,)),
    }
    return variants[field]
