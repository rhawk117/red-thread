"""Ledger lines and case.json: whatever a record holds, it comes back from its text unchanged."""

import json
from typing import TYPE_CHECKING

import msgspec
from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.schemas import (
    case_from_text,
    case_to_text,
    entry_from_line,
    entry_to_line,
)

from tests.casefile.entries.strategies import cases, entries, optional, thread_names

if TYPE_CHECKING:
    from red_thread_casefile.domain import Case, Entry

FIELD_ORDER = (
    'seq',
    'round',
    'kind',
    'text',
    'source',
    'at',
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
DEFAULTED_FIELDS = frozenset({
    'head',
    'verdict',
    'cite',
    'quote',
    'addr',
    'rests_on',
    'refute',
    'diagram',
    'supersedes',
})


class TestEntryLine:
    @given(entry=entries)
    def test_a_line_reads_back_as_the_entry_it_came_from(self, entry: Entry) -> None:
        assert entry_from_line(entry_to_line(entry), entry.thread) == entry

    @given(entry=entries, thread=optional(thread_names))
    def test_the_thread_comes_from_the_file_not_from_the_line(
        self, entry: Entry, thread: str | None
    ) -> None:
        read = entry_from_line(entry_to_line(entry), thread)

        assert read == msgspec.structs.replace(entry, thread=thread)

    @given(entry=entries)
    def test_a_line_holds_no_raw_line_break(self, entry: Entry) -> None:
        line = entry_to_line(entry)

        assert '\n' not in line
        assert '\r' not in line

    @given(entry=entries)
    def test_a_line_is_compact_json_in_field_order_without_defaults_or_thread(
        self, entry: Entry
    ) -> None:
        line = entry_to_line(entry)
        decoded = json.loads(line)
        present = [
            name
            for name in FIELD_ORDER
            if name not in DEFAULTED_FIELDS or getattr(entry, name) not in {None, ()}
        ]

        assert line.startswith(f'{{"seq":{entry.seq},"round":{entry.round},"kind":')
        assert list(decoded) == present
        assert 'thread' not in decoded


class TestDiagramLine:
    diagrams = st.lists(st.text(max_size=20), min_size=2, max_size=5).map('\n'.join)

    @given(entry=entries, diagram=diagrams)
    def test_a_multi_line_diagram_is_one_json_string_and_reads_back_unchanged(
        self, entry: Entry, diagram: str
    ) -> None:
        with_diagram = msgspec.structs.replace(entry, diagram=diagram)

        line = entry_to_line(with_diagram)

        assert '\n' not in line
        assert json.loads(line)['diagram'] == diagram
        assert entry_from_line(line, entry.thread).diagram == diagram

    @given(entry=entries)
    def test_a_line_has_no_diagram_key_when_the_entry_has_none(self, entry: Entry) -> None:
        bare = msgspec.structs.replace(entry, diagram=None)

        assert 'diagram' not in json.loads(entry_to_line(bare))
        assert entry_from_line(entry_to_line(bare), entry.thread).diagram is None


class TestCaseText:
    @given(case=cases)
    def test_the_text_reads_back_as_the_case_it_came_from(self, case: Case) -> None:
        assert case_from_text(case_to_text(case)) == case

    @given(case=cases)
    def test_the_text_is_indented_by_two_and_ends_with_one_line_feed(self, case: Case) -> None:
        text = case_to_text(case)

        assert text.endswith('}\n')
        assert text.split('\n')[1].startswith('  "id": ')
