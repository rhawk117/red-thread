"""Scenarios for what lies in a case file: finding blocks and frontmatter that cannot be read."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tests.params import as_labelled_params, as_params

if TYPE_CHECKING:
    import pytest
    from _pytest.mark import ParameterSet

VALID_BLOCK = ('kind: open', 'text: a question', 'source: scout')
CASE_FIELDS = {
    'id': 'id: 20261121-retry-queue-slowdown',
    'target': 'target: why the retry queue stalls',
    'kind': 'kind: root-cause',
    'bar': 'bar: name the line',
    'created': "created: '2026-11-21T09:30:00+00:00'",
}


def corrupt_block_params() -> list[ParameterSet]:
    blocks = {
        'not-yaml': 'kind: [open',
        'a-list': '- open',
        'a-string': 'just words',
        'missing-source': 'kind: open\ntext: a question',
        'unknown-field': '\n'.join((*VALID_BLOCK, 'colour: red')),
        'unknown-kind': 'kind: guess\ntext: a question\nsource: scout',
        'unknown-verdict': '\n'.join((*VALID_BLOCK, 'verdict: PROBABLY')),
        'text-is-null': 'kind: open\ntext: null\nsource: scout',
        'text-is-empty': "kind: open\ntext: ''\nsource: scout",
        'supersedes-is-a-string': '\n'.join((*VALID_BLOCK, 'supersedes: e1')),
        'cite-is-a-number': '\n'.join((*VALID_BLOCK, 'cite: 3')),
        'value-with-a-colon': 'kind: open\ntext: why: the queue\nsource: scout',
    }
    return as_labelled_params(blocks)


def write_frontmatter(**changes: str | None) -> str:
    fields = {**CASE_FIELDS, **changes}
    lines = (line for line in fields.values() if line is not None)
    return '---\n' + '\n'.join(lines) + '\n---\n\n# why\n'


def corrupt_case_params() -> list[ParameterSet]:
    texts = {
        'empty-file': '',
        'no-frontmatter': '# why the retry queue stalls\n',
        'unclosed-frontmatter': '---\n' + '\n'.join(CASE_FIELDS.values()) + '\n\n# why\n',
        'not-yaml': '---\nid: [\n---\n',
        'a-list': '---\n- one\n---\n',
        'missing-field': write_frontmatter(target=None),
        'unknown-kind': write_frontmatter(kind='kind: hunch'),
        'publish-is-a-string': write_frontmatter(publish="publish: 'yes'"),
        'capabilities-is-a-list': write_frontmatter(capabilities='capabilities: []'),
        'unknown-field': write_frontmatter(colour='colour: red'),
    }
    return as_labelled_params(texts)


@dataclass(slots=True, kw_only=True, frozen=True)
class SeparatorCase:
    name: str
    separator: str
    marks: tuple[pytest.MarkDecorator, ...] = ()


def line_separator_params() -> list[ParameterSet]:
    cases = [
        SeparatorCase(name='form-feed', separator=chr(0x0C)),
        SeparatorCase(name='vertical-tab', separator=chr(0x0B)),
        SeparatorCase(name='file-separator', separator=chr(0x1C)),
        SeparatorCase(name='next-line', separator=chr(0x85)),
        SeparatorCase(name='line-separator', separator=chr(0x2028)),
        SeparatorCase(name='paragraph-separator', separator=chr(0x2029)),
        SeparatorCase(name='carriage-return', separator='\r'),
    ]
    return as_params(cases)
