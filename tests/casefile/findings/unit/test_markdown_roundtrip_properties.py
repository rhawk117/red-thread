"""Whatever a case file holds, it reads back from its Markdown unchanged."""

from typing import TYPE_CHECKING

import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from red_thread_casefile.domain import CASE_FILE, LedgerSource

from tests.casefile.findings.strategies import cases, findings, thread_names, words
from tests.casefile.ledger.builders import create_case
from tests.casefile.ledger.markdown import (
    SCHEMA,
    name_file,
    number_findings,
    write_case_text,
    write_thread_text,
)
from tests.casefile.ledger.memory import name_thread
from tests.core.timekeeping.clock import MOMENT, MOMENT_TEXT

if TYPE_CHECKING:
    from red_thread_casefile.domain import Case, CaseFinding
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


def created_line_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        'line',
        [
            pytest.param(f"created: '{MOMENT_TEXT}'", id='quoted-as-init-writes-it'),
            pytest.param(f'created: {MOMENT_TEXT}', id='bare-as-a-person-might-write-it'),
        ],
    )


def read_files(files: dict[str, str]) -> CaseReading:
    sources = [
        LedgerSource(name=name, thread=name_thread(name), text=text) for name, text in files.items()
    ]
    return SCHEMA.read(sources)


class TestFindingsReadBack:
    finding_lists = st.lists(findings, max_size=5)
    diagrams = st.lists(words, min_size=2, max_size=5).map('\n'.join)

    @given(own=finding_lists, theirs=finding_lists, thread=thread_names)
    def test_findings_written_by_hand_read_back_as_written(
        self, own: list[CaseFinding], theirs: list[CaseFinding], thread: str
    ) -> None:
        in_case = number_findings(own, None)
        in_thread = number_findings(theirs, thread)
        files = {
            CASE_FILE: write_case_text(create_case(), in_case),
            name_file(thread): write_thread_text(in_thread),
        }

        reading = read_files(files)

        assert reading.problems == ()
        assert reading.ledger.findings == (*in_case, *in_thread)

    @given(finding=findings, thread=thread_names)
    def test_the_thread_comes_from_the_file_the_finding_is_in(
        self, finding: CaseFinding, thread: str
    ) -> None:
        files = {
            CASE_FILE: write_case_text(create_case()),
            name_file(thread): write_thread_text([finding]),
        }

        [read] = read_files(files).ledger.findings

        assert read == finding.replace_with(thread=thread)

    @given(finding=findings, diagram=diagrams)
    def test_a_multi_line_diagram_reads_back_with_its_line_breaks(
        self, finding: CaseFinding, diagram: str
    ) -> None:
        with_diagram = finding.replace_with(diagram=diagram)

        [read] = read_files({
            CASE_FILE: write_case_text(create_case(), [with_diagram])
        }).ledger.findings

        assert read.diagram == diagram


class TestCaseFileOpening:
    def test_created_is_written_as_the_quoted_moment_older_case_files_hold(self) -> None:
        lines = SCHEMA.write(create_case()).split('\n')

        assert f"created: '{MOMENT_TEXT}'" in lines

    @created_line_cases()
    def test_created_reads_as_the_moment_whether_quoted_or_bare(self, line: str) -> None:
        written = SCHEMA.write(create_case())
        text = written.replace(f"created: '{MOMENT_TEXT}'", line)

        reading = read_files({CASE_FILE: text})

        assert reading.problems == ()
        assert reading.case is not None
        assert reading.case.created == MOMENT

    @pytest.mark.regression
    @given(case=cases)
    @example(case=create_case().replace_with(target='why the queue\nstalls'))
    def test_the_frontmatter_reads_back_as_the_case_it_came_from(self, case: Case) -> None:
        reading = read_files({CASE_FILE: SCHEMA.write(case)})

        assert reading.problems == ()
        assert reading.case == case

    def test_the_opening_holds_the_frontmatter_the_title_and_round_zero(self) -> None:
        text = SCHEMA.write(create_case())

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
