"""parse_batch: every record becomes a draft or a problem that names its 1-based position."""

from typing import TYPE_CHECKING, Any

import msgspec
from hypothesis import example, given
from hypothesis import strategies as st
from red_thread_casefile.domain import ENTRY_KINDS, VERDICTS
from red_thread_casefile.errors import InvalidFieldError, UnknownFieldError
from red_thread_casefile.schemas import parse_batch

from tests.casefile.entries.strategies import words

if TYPE_CHECKING:
    from collections.abc import Mapping

type Record = Mapping[str, Any]

PADDING = ' \t\n\x0b\x0c\x85\N{LINE SEPARATOR}'


def encode(records: object) -> str:
    return msgspec.json.encode(records).decode()


def with_unknown_field(record: Record, word: str) -> Record:
    return {**record, f'x_{word}': 1}


def insert_at(records: list[Record], index: int, bad: Record) -> list[Record]:
    return [*records[:index], bad, *records[index:]]


class TestParseBatchProperties:
    valid_records = st.fixed_dictionaries(
        {'kind': st.sampled_from(ENTRY_KINDS), 'text': words, 'source': words},
        optional={
            'verdict': st.sampled_from(VERDICTS),
            'cite': words,
            'quote': words,
            'addr': words,
            'rests_on': words,
            'refute': words,
            'diagram': st.lists(words, min_size=1, max_size=4).map('\n'.join),
            'supersedes': st.lists(words, max_size=3),
        },
    )
    bad_kind_records = st.fixed_dictionaries({
        'kind': st.one_of(st.just('nonsense'), st.integers(), st.none()),
        'text': words,
        'source': words,
    })
    unknown_field_records = st.builds(with_unknown_field, valid_records, words)
    any_records = st.lists(
        st.one_of(valid_records, bad_kind_records, unknown_field_records),
        min_size=1,
        max_size=10,
    )
    valid_batches = st.lists(valid_records, min_size=1, max_size=8)
    padding = st.text(alphabet=PADDING, max_size=4)

    @given(records=valid_batches)
    def test_valid_records_become_one_draft_each_in_order(self, records: list[Record]) -> None:
        parsed = parse_batch(encode(records))

        assert parsed.problems == ()
        assert [draft.position for draft in parsed.drafts] == list(range(1, len(records) + 1))
        assert [draft.kind for draft in parsed.drafts] == [record['kind'] for record in records]
        assert [draft.text for draft in parsed.drafts] == [record['text'] for record in records]
        assert [draft.verdict for draft in parsed.drafts] == [
            record.get('verdict') for record in records
        ]
        assert [draft.cite for draft in parsed.drafts] == [record.get('cite') for record in records]
        assert [draft.diagram for draft in parsed.drafts] == [
            record.get('diagram') for record in records
        ]
        assert [draft.supersedes for draft in parsed.drafts] == [
            tuple(record.get('supersedes', ())) for record in records
        ]

    @given(record=valid_records)
    def test_one_object_reads_as_a_batch_of_one(self, record: Record) -> None:
        assert parse_batch(encode(record)) == parse_batch(encode([record]))

    @given(word=words, left=padding, right=padding)
    @example(word='kept', left='  ', right='\n')
    def test_text_fields_are_trimmed(self, word: str, left: str, right: str) -> None:
        padded = f'{left}{word}{right}'
        record = {
            'kind': 'open',
            'text': padded,
            'source': padded,
            'cite': padded,
            'diagram': padded,
        }

        draft = parse_batch(encode([record])).drafts[0]

        assert (draft.text, draft.source, draft.cite, draft.diagram) == (word, word, word, word)

    @given(lines=st.lists(words, min_size=2, max_size=5), padding=padding)
    def test_a_diagram_keeps_the_line_breaks_inside_it(
        self, lines: list[str], padding: str
    ) -> None:
        source = '\n'.join(lines)
        record = {
            'kind': 'open',
            'text': 'a',
            'source': 's',
            'diagram': f'{padding}{source}{padding}',
        }

        draft = parse_batch(encode([record])).drafts[0]

        assert draft.diagram == source
        assert (draft.diagram or '').count('\n') == len(lines) - 1

    @given(blank=st.text(alphabet=PADDING, max_size=4))
    def test_a_blank_diagram_is_no_diagram(self, blank: str) -> None:
        record = {'kind': 'open', 'text': 'a', 'source': 's', 'diagram': blank}

        parsed = parse_batch(encode([record]))

        assert parsed.problems == ()
        assert parsed.drafts[0].diagram is None

    @given(records=valid_batches, bad=bad_kind_records, data=st.data())
    def test_one_bad_kind_yields_one_problem_at_its_position(
        self, records: list[Record], bad: Record, data: st.DataObject
    ) -> None:
        index = data.draw(st.integers(min_value=0, max_value=len(records)))

        parsed = parse_batch(encode(insert_at(records, index, bad)))

        (problem,) = parsed.problems
        assert isinstance(problem, InvalidFieldError)
        assert problem.position == index + 1
        assert problem.field == 'kind'
        expected = [position for position in range(1, len(records) + 2) if position != index + 1]
        assert [draft.position for draft in parsed.drafts] == expected

    @given(records=valid_batches, bad=unknown_field_records, data=st.data())
    def test_one_unknown_field_yields_one_problem_at_its_position(
        self, records: list[Record], bad: Record, data: st.DataObject
    ) -> None:
        index = data.draw(st.integers(min_value=0, max_value=len(records)))

        parsed = parse_batch(encode(insert_at(records, index, bad)))

        (problem,) = parsed.problems
        assert isinstance(problem, UnknownFieldError)
        assert problem.position == index + 1
        assert problem.field.startswith('x_')
        assert len(parsed.drafts) == len(records)

    @given(records=any_records)
    def test_every_record_is_one_draft_or_one_problem(self, records: list[Record]) -> None:
        parsed = parse_batch(encode(records))

        positions = [item.position for item in (*parsed.drafts, *parsed.problems)]
        assert sorted(positions) == list(range(1, len(records) + 1))
