"""Scenarios for what lies in a ledger file."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from tests.params import as_params

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet

VALID_LINE = (
    '{"seq": 1, "round": 1, "kind": "open", "text": "a question", '
    '"source": "scout", "at": "2026-11-21T09:30:00+00:00"}'
)


def corrupt_line_params() -> list[ParameterSet]:
    lines = {
        'not-json': 'this is not json',
        'truncated-json': '{"seq": 1, "round": 1, "kind": "open"',
        'json-array': '[1, 2, 3]',
        'json-string': '"a string"',
        'json-null': 'null',
        'object-missing-fields': '{"seq": 1}',
        'object-with-an-unknown-field': VALID_LINE.replace('}', ', "colour": "red"}'),
        'seq-is-a-string': VALID_LINE.replace('"seq": 1', '"seq": "1"'),
        'round-is-a-float': VALID_LINE.replace('"round": 1', '"round": 1.5'),
        'unknown-kind': VALID_LINE.replace('"open"', '"guess"'),
        'unknown-verdict': VALID_LINE.replace('}', ', "verdict": "PROBABLY"}'),
        'text-is-null': VALID_LINE.replace('"a question"', 'null'),
        'supersedes-is-a-string': VALID_LINE.replace('}', ', "supersedes": "e1"}'),
        'cite-is-a-number': VALID_LINE.replace('}', ', "cite": 3}'),
    }
    return [pytest.param(line, id=name) for name, line in lines.items()]


CASE_RECORD = (
    '{"id": "20261121-retry-queue-slowdown", "target": "why the retry queue stalls", '
    '"kind": "root-cause", "bar": "name the line", "created": "2026-11-21T09:30:00+00:00"}'
)


def corrupt_case_params() -> list[ParameterSet]:
    texts = {
        'not-json': 'this is not json',
        'empty-file': '',
        'truncated-json': CASE_RECORD[:-1],
        'json-array': '[]',
        'json-null': 'null',
        'missing-field': CASE_RECORD.replace('"target": "why the retry queue stalls", ', ''),
        'unknown-kind': CASE_RECORD.replace('"root-cause"', '"hunch"'),
        'publish-is-a-string': CASE_RECORD.replace('}', ', "publish": "yes"}'),
        'capabilities-is-a-list': CASE_RECORD.replace('}', ', "capabilities": []}'),
    }
    return [pytest.param(text, id=name) for name, text in texts.items()]


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
