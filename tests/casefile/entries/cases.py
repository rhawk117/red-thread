"""Scenarios for the shape of a submitted batch."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.errors import InvalidFieldError, UnknownFieldError

from tests.params import as_labelled_params, as_params

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet
    from red_thread_casefile.errors import CaseFileError

VALID = {'kind': 'open', 'text': 'what stalls the queue', 'source': 'scout'}


@dataclass(slots=True, kw_only=True, frozen=True)
class ShapeCase:
    name: str
    record: dict[str, object]
    error_type: type[CaseFileError]
    field_name: str
    marks: tuple[pytest.MarkDecorator, ...] = field(default=())

    @property
    def param(self) -> ParameterSet:
        return pytest.param(self, id=self.name, marks=self.marks)


def shape_problem_params() -> list[ParameterSet]:
    cases = [
        ShapeCase(
            name='unknown-field',
            record={**VALID, 'colour': 'red'},
            error_type=UnknownFieldError,
            field_name='colour',
        ),
        ShapeCase(
            name='caller-supplied-seq',
            record={**VALID, 'seq': 9},
            error_type=UnknownFieldError,
            field_name='seq',
        ),
        ShapeCase(
            name='caller-supplied-time',
            record={**VALID, 'at': '2026-01-01T00:00:00+00:00'},
            error_type=UnknownFieldError,
            field_name='at',
        ),
        ShapeCase(
            name='caller-supplied-head',
            record={**VALID, 'head': 'abc'},
            error_type=UnknownFieldError,
            field_name='head',
        ),
        ShapeCase(
            name='caller-supplied-round',
            record={**VALID, 'round': 2},
            error_type=UnknownFieldError,
            field_name='round',
        ),
        ShapeCase(
            name='missing-kind',
            record={'text': 'a', 'source': 'scout'},
            error_type=InvalidFieldError,
            field_name='kind',
        ),
        ShapeCase(
            name='unknown-kind',
            record={**VALID, 'kind': 'finding'},
            error_type=InvalidFieldError,
            field_name='kind',
        ),
        ShapeCase(
            name='kind-in-the-wrong-case',
            record={**VALID, 'kind': 'Known'},
            error_type=InvalidFieldError,
            field_name='kind',
        ),
        ShapeCase(
            name='blank-text',
            record={**VALID, 'text': '   '},
            error_type=InvalidFieldError,
            field_name='text',
        ),
        ShapeCase(
            name='non-string-text',
            record={**VALID, 'text': 5},
            error_type=InvalidFieldError,
            field_name='text',
        ),
        ShapeCase(
            name='missing-source',
            record={'kind': 'open', 'text': 'a'},
            error_type=InvalidFieldError,
            field_name='source',
        ),
        ShapeCase(
            name='blank-source',
            record={**VALID, 'source': ''},
            error_type=InvalidFieldError,
            field_name='source',
        ),
        ShapeCase(
            name='unknown-verdict',
            record={**VALID, 'verdict': 'VERIFYD'},
            error_type=InvalidFieldError,
            field_name='verdict',
        ),
        ShapeCase(
            name='lowercase-verdict',
            record={**VALID, 'verdict': 'verified'},
            error_type=InvalidFieldError,
            field_name='verdict',
        ),
        ShapeCase(
            name='non-string-cite',
            record={**VALID, 'cite': 5},
            error_type=InvalidFieldError,
            field_name='cite',
        ),
        ShapeCase(
            name='list-quote',
            record={**VALID, 'quote': ['a']},
            error_type=InvalidFieldError,
            field_name='quote',
        ),
        ShapeCase(
            name='non-string-refute',
            record={**VALID, 'refute': True},
            error_type=InvalidFieldError,
            field_name='refute',
        ),
        ShapeCase(
            name='non-string-diagram',
            record={**VALID, 'diagram': 5},
            error_type=InvalidFieldError,
            field_name='diagram',
        ),
        ShapeCase(
            name='list-diagram',
            record={**VALID, 'diagram': ['flowchart TD']},
            error_type=InvalidFieldError,
            field_name='diagram',
        ),
        ShapeCase(
            name='supersedes-is-a-string',
            record={**VALID, 'supersedes': 'e1'},
            error_type=InvalidFieldError,
            field_name='supersedes',
        ),
        ShapeCase(
            name='supersedes-holds-a-number',
            record={**VALID, 'supersedes': ['e1', 2]},
            error_type=InvalidFieldError,
            field_name='supersedes',
        ),
    ]
    return as_params(cases)


def malformed_batch_params() -> list[ParameterSet]:
    texts = {
        'not-json': 'this is not json',
        'truncated-json': '[{"kind": "open"',
        'empty-array': '[]',
        'bare-number': '5',
        'bare-string': '"open"',
        'null': 'null',
        'array-of-numbers': '[1, 2]',
        'object-beside-a-number': '[{"kind": "open", "text": "a", "source": "s"}, 3]',
        'empty-input': '',
    }
    return as_labelled_params(texts)
