"""Documents for the page and Markdown writers, with one field carrying the text under test."""

from dataclasses import replace
from typing import TYPE_CHECKING, Literal, cast

from red_thread_casefile.policy import Finding
from red_thread_casefile.views import Document, Fact, Item, Section

if TYPE_CHECKING:
    from red_thread_casefile.domain import EntryKind, Verdict
    from red_thread_casefile.policy import CiteState

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
    'item-verdict',
    'item-at',
    'item-quote',
    'item-state',
    'section-note',
    'section-kind',
    'fact-label',
    'fact-value',
    'fact-url-value',
    'retired-text',
    'retired-note',
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
    'item-verdict',
    'item-at',
    'item-quote',
    'item-state',
    'section-note',
    'section-kind',
    'fact-label',
    'fact-value',
    'fact-url-value',
    'retired-text',
    'retired-note',
)
PLAIN_URL = 'https://example.invalid/docs'
SCRIPT = '<script>alert(1)</script>'
PAYLOADS = (
    SCRIPT,
    '</title><script>alert(1)</script>',
    '"><img src=x onerror=alert(1)>',
    "'><svg onload=alert(1)>",
    '<SCRIPT SRC=//evil.invalid/x.js></SCRIPT>',
    '&lt;script&gt;',
    '<!-- <script> -->',
    '</pre><script>alert(1)</script>',
    '</button><script>alert(1)</script>',
)


def create_marked_item(
    *, ref: str = 'e1', kind: EntryKind | None = 'known', thread: str | None = None
) -> Item:
    return Item(text='a claim', ref=ref, kind=kind, thread=thread)


def create_document(*items: Item, title: str = 'A case', prose: tuple[str, ...] = ()) -> Document:
    section = Section(title='Findings', items=items, prose=prose)
    return Document(title=title, summary=('Case summary line',), sections=(section,))


def create_finding(state: str) -> Finding:
    return Finding(ref='e1', cite='src/queue.py:3', state=cast('CiteState', state))


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
    retired = Item(text='gone', ref='e9', kind='open')
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
        'item-verdict': create_document(replace(item, verdict=cast('Verdict', text)), other),
        'item-at': create_document(replace(item, at=text), other),
        'item-quote': create_document(replace(item, quote=text), other),
        'item-state': create_document(replace(item, finding=create_finding(text)), other),
        'section-note': replace(base, sections=(replace(section, note=text),)),
        'section-kind': replace(base, sections=(replace(section, kind=cast('EntryKind', text)),)),
        'fact-label': replace(base, facts=(Fact(label=text, value='plain'),)),
        'fact-value': replace(base, facts=(Fact(label='Label', value=text),)),
        'fact-url-value': replace(base, facts=(Fact(label='Label', value=f'{PLAIN_URL}/{text}'),)),
        'retired-text': replace(base, retired=(replace(retired, text=text),)),
        'retired-note': replace(base, retired=(replace(retired, notes=(text,)),)),
    }
    return variants[field]
