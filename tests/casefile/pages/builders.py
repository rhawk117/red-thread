"""Documents for the page and Markdown writers, with one field carrying the text under test."""

from typing import TYPE_CHECKING, Literal, cast, get_args

import pytest
from red_thread_casefile.documents import Citation, EntryList
from red_thread_casefile.packaged import load_wording
from red_thread_casefile.policy import Finding
from red_thread_core.documents import Fact, Flowchart, Section, parse_line, parse_value

from tests.casefile.writers.builders import create_document, create_entry_node

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet
    from red_thread_casefile.documents import EntryNode
    from red_thread_casefile.domain import EntryKind, Verdict
    from red_thread_casefile.policy import CiteState
    from red_thread_core.documents import Document

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

DOCUMENT_FIELDS: tuple[DocumentField, ...] = get_args(DocumentField.__value__)
STAMP_DAY = '2026-11-21'
PLAIN_URL = 'https://example.invalid/docs'
CITED_PATH = 'src/queue.py:3'
SCRIPT = '<script>alert(1)</script>'
DIAGRAM = 'flowchart TD\n  A["one"] --> B["two"]\n  B --> C'
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


def payload_params() -> list[ParameterSet]:
    return [
        pytest.param(payload, id=f'payload-{number}') for number, payload in enumerate(PAYLOADS)
    ]


def create_marked_entry(
    *, ref: str = 'e1', kind: EntryKind = 'known', thread: str | None = None
) -> EntryNode:
    return create_entry_node(ref=ref).replace_with(kind=kind, thread=thread)


def create_finding(state: str) -> Finding:
    return Finding(ref='e1', cite=CITED_PATH, state=cast('CiteState', state))


def create_cited_entry(citation: Citation) -> EntryNode:
    return create_marked_entry(thread='T1').replace_with(citation=citation)


def create_appendix(title: str, entry: EntryNode) -> tuple[Section, ...]:
    return (Section(title=title, blocks=(EntryList(entries=(entry,)),), folded=True),)


def create_document_carrying(field: DocumentField, text: str) -> Document:
    citation = Citation(target=CITED_PATH)
    entry = create_cited_entry(citation).replace_with(
        claim=parse_line('plain text'),
        notes=(load_wording().write_note('rests_on', 'plain'),),
        lead='1111111',
    )
    other = create_entry_node('other text', 'e2').replace_with(kind='open')
    retired = create_entry_node('gone', 'e9').replace_with(kind='open')
    base = create_document(entry, other)
    section = base.sections[0]
    chart = Section(title='Map', blocks=(Flowchart(lines=(text,)),))
    variants = {
        'title': base.replace_with(title=text),
        'summary': base.replace_with(summary=(parse_line(text),)),
        'section-title': base.replace_with(sections=(section.replace_with(title=text),)),
        'prose': create_document(entry, other, prose=(text,)),
        'item-text': create_document(entry.replace_with(claim=parse_line(text)), other),
        'item-cite': create_document(entry.replace_with(citation=Citation(target=text)), other),
        'item-url-cite': create_document(
            entry.replace_with(citation=Citation(target=f'{PLAIN_URL}/{text}')), other
        ),
        'item-ref': create_document(entry.replace_with(ref=text), other),
        'item-note': create_document(
            entry.replace_with(notes=(load_wording().write_note('source', text),)), other
        ),
        'item-flag': create_document(entry.replace_with(lead=text), other),
        'item-kind': create_document(entry.replace_with(kind=cast('EntryKind', text)), other),
        'item-thread': create_document(entry.replace_with(thread=text), other),
        'item-diagram': create_document(entry.replace_with(diagram=text), other),
        'map-line': base.replace_with(appendix=(chart,)),
        'item-verdict': create_document(entry.replace_with(verdict=cast('Verdict', text)), other),
        'item-at': create_document(entry.replace_with(at=f'{STAMP_DAY}{text}'), other),
        'item-quote': create_document(
            entry.replace_with(citation=citation.replace_with(quote=text)), other
        ),
        'item-state': create_document(
            entry.replace_with(citation=citation.replace_with(finding=create_finding(text))), other
        ),
        'section-note': base.replace_with(sections=(section.replace_with(note=text),)),
        'section-kind': base.replace_with(
            sections=(section.replace_with(kind=cast('EntryKind', text)),)
        ),
        'fact-label': base.replace_with(facts=(Fact(label=text, value=parse_value('plain')),)),
        'fact-value': base.replace_with(facts=(Fact(label='Label', value=parse_value(text)),)),
        'fact-url-value': base.replace_with(
            facts=(Fact(label='Label', value=parse_value(f'{PLAIN_URL}/{text}')),)
        ),
        'retired-text': base.replace_with(
            appendix=create_appendix('Retired', retired.replace_with(claim=parse_line(text)))
        ),
        'retired-note': base.replace_with(
            appendix=create_appendix(
                'Retired', retired.replace_with(notes=(load_wording().write_note('source', text),))
            ),
        ),
    }
    return variants[field]
