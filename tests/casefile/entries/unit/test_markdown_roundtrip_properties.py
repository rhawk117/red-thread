"""Whatever a case file holds, it reads back from its Markdown unchanged."""

from typing import TYPE_CHECKING

import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from msgspec.structs import replace
from red_thread_casefile.domain import CASE_FILE, LedgerSource
from red_thread_casefile.schemas import read_case_file, write_case_file

from tests.casefile.entries.strategies import cases, entries, thread_names, words
from tests.casefile.ledger.builders import create_case
from tests.casefile.ledger.markdown import (
    name_file,
    number_entries,
    write_case_text,
    write_thread_text,
)
from tests.casefile.ledger.memory import name_thread

if TYPE_CHECKING:
    from red_thread_casefile.domain import Case, Entry
    from red_thread_casefile.schemas import CaseReading

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


def read_files(files: dict[str, str]) -> CaseReading:
    sources = [
        LedgerSource(name=name, thread=name_thread(name), text=text) for name, text in files.items()
    ]
    return read_case_file(sources)


class TestEntriesReadBack:
    entry_lists = st.lists(entries, max_size=5)
    diagrams = st.lists(words, min_size=2, max_size=5).map('\n'.join)

    @given(own=entry_lists, theirs=entry_lists, thread=thread_names)
    def test_entries_written_by_hand_read_back_as_written(
        self, own: list[Entry], theirs: list[Entry], thread: str
    ) -> None:
        in_case = number_entries(own, None)
        in_thread = number_entries(theirs, thread)
        files = {
            CASE_FILE: write_case_text(create_case(), in_case),
            name_file(thread): write_thread_text(in_thread),
        }

        reading = read_files(files)

        assert reading.problems == ()
        assert reading.ledger.entries == (*in_case, *in_thread)

    @given(entry=entries, thread=thread_names)
    def test_the_thread_comes_from_the_file_the_entry_is_in(
        self, entry: Entry, thread: str
    ) -> None:
        files = {
            CASE_FILE: write_case_text(create_case()),
            name_file(thread): write_thread_text([entry]),
        }

        [read] = read_files(files).ledger.entries

        assert read == replace(entry, thread=thread)

    @given(entry=entries, diagram=diagrams)
    def test_a_multi_line_diagram_reads_back_with_its_line_breaks(
        self, entry: Entry, diagram: str
    ) -> None:
        with_diagram = replace(entry, diagram=diagram)

        [read] = read_files({
            CASE_FILE: write_case_text(create_case(), [with_diagram])
        }).ledger.entries

        assert read.diagram == diagram


class TestCaseFileOpening:
    @pytest.mark.regression
    @given(case=cases)
    @example(case=replace(create_case(), target='why the queue\nstalls'))
    def test_the_frontmatter_reads_back_as_the_case_it_came_from(self, case: Case) -> None:
        reading = read_files({CASE_FILE: write_case_file(case)})

        assert reading.problems == ()
        assert reading.case == case

    def test_the_opening_holds_the_frontmatter_the_title_and_round_zero(self) -> None:
        text = write_case_file(create_case())

        lines = text.split('\n')
        closing = lines.index('---', 1)
        keys = [line.partition(':')[0] for line in lines[1:closing] if not line.startswith(' ')]
        assert lines[0] == '---'
        assert keys == list(CASE_FIELDS)
        assert lines[closing + 1 :] == [
            '',
            '# why the retry queue stalls',
            '',
            '## Round 0 · 2026-11-21 · 1111111',
            '',
        ]
