"""Turning submitted batch text into drafts, or into every shape problem it has."""

import json
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.domain import Draft
from red_thread_casefile.errors import InvalidFieldError, MalformedBatchError
from red_thread_casefile.schemas import parse_batch

from tests.casefile.entries.cases import VALID, malformed_batch_params, shape_problem_params

if TYPE_CHECKING:
    from tests.casefile.entries.cases import ShapeCase


def shape_problem_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', shape_problem_params())


def malformed_batch_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('text', malformed_batch_params())


def unparsable_batch_cases() -> pytest.MarkDecorator:
    texts = {
        'not-json': 'this is not json',
        'truncated-json': '[{"kind": "open"',
        'empty-input': '',
    }
    return pytest.mark.parametrize(
        'text', [pytest.param(text, id=name) for name, text in texts.items()]
    )


class TestParseBatch:
    @shape_problem_cases()
    def test_shape_problem_is_reported_with_its_field(self, case: ShapeCase) -> None:
        parsed = parse_batch(json.dumps([case.record]))

        assert parsed.drafts == ()
        assert len(parsed.problems) == 1
        problem = parsed.problems[0]
        assert type(problem) is case.error_type
        assert problem.field == case.field_name
        assert problem.position == 1

    @malformed_batch_cases()
    def test_unusable_batch_is_refused_whole(self, text: str) -> None:
        with pytest.raises(MalformedBatchError):
            parse_batch(text)

    @unparsable_batch_cases()
    def test_text_that_is_not_json_says_so_with_the_parser_message(self, text: str) -> None:
        with pytest.raises(MalformedBatchError) as raised:
            parse_batch(text)

        assert raised.value.reason.startswith('it is not JSON (')
        assert raised.value.reason.endswith(')')
        assert len(raised.value.reason) > len('it is not JSON ()')

    def test_valid_json_with_no_entries_is_not_called_unparsable(self) -> None:
        with pytest.raises(MalformedBatchError) as raised:
            parse_batch('[]')

        assert raised.value.reason == 'it holds no entries'

    def test_an_item_that_is_not_an_object_is_named_as_such(self) -> None:
        with pytest.raises(MalformedBatchError) as raised:
            parse_batch('[1, 2]')

        assert raised.value.reason == 'an item is not a JSON object'

    def test_single_object_is_a_batch_of_one(self) -> None:
        parsed = parse_batch(json.dumps(VALID))

        assert parsed.problems == ()
        assert [(draft.position, draft.kind, draft.text) for draft in parsed.drafts] == [
            (1, 'open', 'what stalls the queue')
        ]

    def test_good_and_bad_entries_keep_their_positions(self) -> None:
        records = [VALID, {**VALID, 'kind': 'nope'}, VALID, {**VALID, 'verdict': 'x'}]

        parsed = parse_batch(json.dumps(records))

        assert [draft.position for draft in parsed.drafts] == [1, 3]
        assert [problem.position for problem in parsed.problems] == [2, 4]
        assert all(isinstance(problem, InvalidFieldError) for problem in parsed.problems)

    def test_every_field_reaches_the_draft(self) -> None:
        record = {
            'kind': 'known',
            'text': 'the sleep blocks',
            'source': 'scout',
            'verdict': 'VERIFIED',
            'cite': 'src/queue.py:3',
            'quote': 'time.sleep',
            'addr': 'src/queue.py#retry',
            'rests_on': 'a caveat',
            'refute': 'an observation',
            'supersedes': ['e1', 'T1.e2'],
        }

        parsed = parse_batch(json.dumps(record))

        assert parsed.drafts == (
            Draft(
                position=1,
                kind='known',
                text='the sleep blocks',
                source='scout',
                verdict='VERIFIED',
                cite='src/queue.py:3',
                quote='time.sleep',
                addr='src/queue.py#retry',
                rests_on='a caveat',
                refute='an observation',
                supersedes=('e1', 'T1.e2'),
            ),
        )

    def test_surrounding_whitespace_is_stripped_and_blank_options_are_dropped(self) -> None:
        record = {
            **VALID,
            'text': '  padded  ',
            'source': ' scout ',
            'cite': '   ',
            'verdict': None,
        }

        parsed = parse_batch(json.dumps(record))

        assert [
            (draft.text, draft.source, draft.cite, draft.verdict) for draft in parsed.drafts
        ] == [('padded', 'scout', None, None)]
