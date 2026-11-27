"""Documents for the page and Markdown writers, with one field carrying the text under test."""

from typing import TYPE_CHECKING, Literal, cast, get_args

import pytest
from red_thread_casefile.documents import CitationNode, FindingList
from red_thread_casefile.packaged import load_wording
from red_thread_casefile.policy import CitationCheck
from red_thread_core.documents import Fact, Flowchart, Section, parse_line, parse_value

from tests.casefile.writers.builders import create_document, create_finding_node

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet
    from red_thread_casefile.documents import FindingNode
    from red_thread_casefile.domain import FindingKind, Verdict
    from red_thread_casefile.policy import CitationState
    from red_thread_core.documents import Document

type DocumentField = Literal[
    'title',
    'summary',
    'section-title',
    'prose',
    'item-text',
    'item-cite',
    'item-url-cite',
    'item-finding-id',
    'item-note',
    'item-flag',
    'item-kind',
    'item-thread',
    'item-diagram',
    'map-line',
    'item-verdict',
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


def create_marked_finding(
    *, finding_id: str = 'e1', kind: FindingKind = 'known', thread: str | None = None
) -> FindingNode:
    return create_finding_node(finding_id=finding_id).replace_with(kind=kind, thread=thread)


def create_citation_check(state: str) -> CitationCheck:
    return CitationCheck(finding_id='e1', citation=CITED_PATH, state=cast('CitationState', state))


def create_cited_finding(citation_node: CitationNode) -> FindingNode:
    return create_marked_finding(thread='T1').replace_with(citation_node=citation_node)


def create_appendix(title: str, finding: FindingNode) -> tuple[Section, ...]:
    return (Section(title=title, blocks=(FindingList(findings=(finding,)),), folded=True),)


def create_document_carrying(field: DocumentField, text: str) -> Document:
    citation_node = CitationNode(target=CITED_PATH)
    finding = create_cited_finding(citation_node).replace_with(
        claim=parse_line('plain text'),
        notes=(load_wording().write_note('rests_on', 'plain'),),
        lead='1111111',
    )
    other = create_finding_node('other text', 'e2').replace_with(kind='open')
    retired = create_finding_node('gone', 'e9').replace_with(kind='open')
    base = create_document(finding, other)
    section = base.sections[0]
    chart = Section(title='Map', blocks=(Flowchart(lines=(text,)),))
    variants = {
        'title': base.replace_with(title=text),
        'summary': base.replace_with(summary=(parse_line(text),)),
        'section-title': base.replace_with(sections=(section.replace_with(title=text),)),
        'prose': create_document(finding, other, prose=(text,)),
        'item-text': create_document(finding.replace_with(claim=parse_line(text)), other),
        'item-cite': create_document(
            finding.replace_with(citation_node=CitationNode(target=text)), other
        ),
        'item-url-cite': create_document(
            finding.replace_with(citation_node=CitationNode(target=f'{PLAIN_URL}/{text}')), other
        ),
        'item-finding-id': create_document(finding.replace_with(finding_id=text), other),
        'item-note': create_document(
            finding.replace_with(notes=(load_wording().write_note('source', text),)), other
        ),
        'item-flag': create_document(finding.replace_with(lead=text), other),
        'item-kind': create_document(finding.replace_with(kind=cast('FindingKind', text)), other),
        'item-thread': create_document(finding.replace_with(thread=text), other),
        'item-diagram': create_document(finding.replace_with(diagram=text), other),
        'map-line': base.replace_with(appendix=(chart,)),
        'item-verdict': create_document(finding.replace_with(verdict=cast('Verdict', text)), other),
        'item-quote': create_document(
            finding.replace_with(citation_node=citation_node.replace_with(quote=text)), other
        ),
        'item-state': create_document(
            finding.replace_with(
                citation_node=citation_node.replace_with(citation_check=create_citation_check(text))
            ),
            other,
        ),
        'section-note': base.replace_with(sections=(section.replace_with(note=text),)),
        'section-kind': base.replace_with(
            sections=(section.replace_with(kind=cast('FindingKind', text)),)
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
