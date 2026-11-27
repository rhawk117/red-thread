"""Scenarios for a finding's yaml block: fields it may not hold, and blocks no one can read."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from tests.params import as_labelled_params, as_params

if TYPE_CHECKING:
    import pytest
    from _pytest.mark import ParameterSet

VALID = {'kind': 'open', 'text': 'what stalls the queue', 'source': 'scout'}


@dataclass(slots=True, kw_only=True, frozen=True)
class ShapeCase:
    name: str
    record: dict[str, object]
    field_name: str
    marks: tuple[pytest.MarkDecorator, ...] = field(default=())


def stamp_field_cases() -> list[ShapeCase]:
    stamps = {
        'finding_number': 9,
        'round': 2,
        'at': '2026-11-21',
        'head': 'abc1234',
        'thread': 'T1',
    }
    return [
        ShapeCase(name=f'block-sets-{name}', record={**VALID, name: value}, field_name=name)
        for name, value in stamps.items()
    ]


def shape_problem_params() -> list[ParameterSet]:
    cases = [
        ShapeCase(name='unknown-field', record={**VALID, 'colour': 'red'}, field_name='colour'),
        *stamp_field_cases(),
        ShapeCase(
            name='missing-kind',
            record={'text': 'a', 'source': 'scout'},
            field_name='kind',
        ),
        ShapeCase(name='unknown-kind', record={**VALID, 'kind': 'guess'}, field_name='kind'),
        ShapeCase(
            name='kind-in-the-wrong-case', record={**VALID, 'kind': 'Known'}, field_name='kind'
        ),
        ShapeCase(name='blank-text', record={**VALID, 'text': '   '}, field_name='text'),
        ShapeCase(name='non-string-text', record={**VALID, 'text': 5}, field_name='text'),
        ShapeCase(
            name='missing-source',
            record={'kind': 'open', 'text': 'a'},
            field_name='source',
        ),
        ShapeCase(name='blank-source', record={**VALID, 'source': ' '}, field_name='source'),
        ShapeCase(
            name='unknown-verdict', record={**VALID, 'verdict': 'PROBABLY'}, field_name='verdict'
        ),
        ShapeCase(
            name='lowercase-verdict', record={**VALID, 'verdict': 'verified'}, field_name='verdict'
        ),
        ShapeCase(name='non-string-cite', record={**VALID, 'cite': 3}, field_name='cite'),
        ShapeCase(name='blank-cite', record={**VALID, 'cite': '   '}, field_name='cite'),
        ShapeCase(name='list-quote', record={**VALID, 'quote': ['a']}, field_name='quote'),
        ShapeCase(name='non-string-refute', record={**VALID, 'refute': 7}, field_name='refute'),
        ShapeCase(name='blank-rests-on', record={**VALID, 'rests_on': ''}, field_name='rests_on'),
        ShapeCase(name='non-string-diagram', record={**VALID, 'diagram': 1}, field_name='diagram'),
        ShapeCase(
            name='list-diagram', record={**VALID, 'diagram': ['flowchart TD']}, field_name='diagram'
        ),
        ShapeCase(
            name='blank-diagram', record={**VALID, 'diagram': ' \n  \n'}, field_name='diagram'
        ),
        ShapeCase(
            name='supersedes-is-a-string',
            record={**VALID, 'supersedes': 'e1'},
            field_name='supersedes',
        ),
        ShapeCase(
            name='supersedes-holds-a-number',
            record={**VALID, 'supersedes': [1]},
            field_name='supersedes',
        ),
    ]
    return as_params(cases)


def unreadable_block_params() -> list[ParameterSet]:
    blocks = {
        'empty-block': '',
        'null': 'null\n',
        'bare-number': '5\n',
        'bare-string': 'open\n',
        'list-of-mappings': '- kind: open\n  text: a\n  source: scout\n',
        'unclosed-quote': 'kind: open\ntext: "what stalls\nsource: scout\n',
        'tab-indented': 'kind: open\n\ttext: a\n',
    }
    return as_labelled_params(blocks)
