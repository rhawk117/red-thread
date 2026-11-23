"""Ledger lines and case files read back as exactly what was written."""

import json

from hypothesis import given
from hypothesis import strategies as st
from msgspec.structs import replace
from red_thread_casefile.domain import CASE_KINDS, ENTRY_KINDS, VERDICTS, Capabilities, Case, Entry
from red_thread_casefile.schemas import (
    case_from_text,
    case_to_text,
    entry_from_line,
    entry_to_line,
)

from tests.casefile.ledger.builders import create_case, create_entry


def make_thread_name(number: int) -> str:
    return f'T{number}'


maybe_text = st.none() | st.text()
RETIRED_FLAG = 'navigation_tool'
REQUIRED_FIELDS = ('seq', 'round', 'kind', 'text', 'source', 'at')
OPTIONAL_FIELDS = (
    'head',
    'verdict',
    'cite',
    'quote',
    'addr',
    'rests_on',
    'refute',
    'diagram',
    'supersedes',
)
CASE_FIELDS = (
    'id',
    'target',
    'kind',
    'bar',
    'created',
    'publish',
    'head',
    'page_url',
    'capabilities',
)


class TestEntryLines:
    threads = st.none() | st.integers(min_value=1, max_value=99).map(make_thread_name)
    entries = st.builds(
        Entry,
        seq=st.integers(min_value=1, max_value=10**6),
        round=st.integers(min_value=0, max_value=1000),
        kind=st.sampled_from(ENTRY_KINDS),
        text=st.text(),
        source=st.text(),
        at=st.text(),
        head=maybe_text,
        verdict=st.none() | st.sampled_from(VERDICTS),
        cite=maybe_text,
        quote=maybe_text,
        addr=maybe_text,
        rests_on=maybe_text,
        refute=maybe_text,
        diagram=maybe_text,
        supersedes=st.lists(st.text(), max_size=4).map(tuple),
        thread=threads,
    )

    @given(entry=entries)
    def test_line_reads_back_as_the_entry_it_was_written_from(self, entry: Entry) -> None:
        line = entry_to_line(entry)

        assert entry_from_line(line, entry.thread) == entry

    @given(entry=entries)
    def test_line_is_one_json_object_on_one_line(self, entry: Entry) -> None:
        line = entry_to_line(entry)

        assert '\n' not in line
        assert '\r' not in line
        assert isinstance(json.loads(line), dict)

    @given(entry=entries)
    def test_thread_comes_from_the_file_and_never_from_the_line(self, entry: Entry) -> None:
        stored = json.loads(entry_to_line(entry))

        assert 'thread' not in stored
        assert entry_from_line(entry_to_line(entry), 'T7').thread == 'T7'

    @given(entry=entries)
    def test_line_is_compact_json_with_one_space_free_separator_pair(self, entry: Entry) -> None:
        line = entry_to_line(entry)

        stored = json.loads(line)

        assert line == json.dumps(stored, separators=(',', ':'), ensure_ascii=False)

    @given(entry=entries)
    def test_fields_follow_the_order_of_the_entry_record(self, entry: Entry) -> None:
        stored = json.loads(entry_to_line(entry))

        expected = [name for name in (*REQUIRED_FIELDS, *OPTIONAL_FIELDS) if name in stored]
        assert list(stored) == expected

    @given(entry=entries)
    def test_a_field_is_in_the_line_exactly_when_it_holds_more_than_its_default(
        self, entry: Entry
    ) -> None:
        stored = json.loads(entry_to_line(entry))

        set_fields = {name for name in OPTIONAL_FIELDS if getattr(entry, name) not in (None, ())}
        assert set(stored) == {*REQUIRED_FIELDS, *set_fields}

    def test_unset_fields_are_left_out_of_the_line(self) -> None:
        stored = json.loads(entry_to_line(create_entry(seq=1)))

        assert set(stored) == {'seq', 'round', 'kind', 'text', 'source', 'at', 'head'}

    def test_text_is_kept_readable_and_not_escaped_to_ascii(self) -> None:
        line = entry_to_line(replace(create_entry(), text='café queue'))

        assert 'café' in line


class TestCaseText:
    cases = st.builds(
        Case,
        id=st.text(min_size=1),
        target=st.text(),
        kind=st.sampled_from(CASE_KINDS),
        bar=st.text(),
        created=st.text(),
        publish=st.booleans(),
        head=maybe_text,
        page_url=maybe_text,
        capabilities=st.builds(
            Capabilities,
            languages=st.lists(st.text(), max_size=5).map(tuple),
        ),
    )

    @given(case=cases)
    def test_case_reads_back_as_the_case_it_was_written_from(self, case: Case) -> None:
        assert case_from_text(case_to_text(case)) == case

    def test_case_written_with_the_retired_flag_still_reads_back(self) -> None:
        document = json.loads(case_to_text(create_case()))
        document['capabilities'][RETIRED_FLAG] = True

        assert case_from_text(json.dumps(document)) == create_case()

    @given(case=cases)
    def test_text_is_indented_by_two_and_ends_with_one_newline(self, case: Case) -> None:
        text = case_to_text(case)

        assert text == json.dumps(json.loads(text), indent=2, ensure_ascii=False) + '\n'

    @given(case=cases)
    def test_fields_follow_the_order_of_the_case_record(self, case: Case) -> None:
        assert list(json.loads(case_to_text(case))) == list(CASE_FIELDS)
