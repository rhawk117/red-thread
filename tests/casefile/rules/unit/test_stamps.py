"""What a finding takes from its round heading, and how findings are numbered in each file."""

from datetime import date
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.domain import CASE_FILE
from red_thread_casefile.errors import MalformedCaseError, NumberingError

from tests.casefile.ledger.builders import create_case, create_finding
from tests.casefile.ledger.markdown import write_case_text
from tests.casefile.ledger.memory import HEAD
from tests.casefile.rules.layout_cases import layout_params, write_raw_finding
from tests.casefile.rules.supersede_cases import numbering_params

if TYPE_CHECKING:
    from tests.casefile.ledger.builders import CaseHarness
    from tests.casefile.rules.layout_cases import LayoutCase
    from tests.casefile.rules.supersede_cases import NumberingCase


def numbering_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', numbering_params())


def layout_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', layout_params())


class TestRoundStamps:
    rounds = (
        '## Round 2 · 2026-11-22 · abc1234',
        write_raw_finding('### e1'),
        write_raw_finding('### e2'),
        '## Round 3 · 2026-11-23 · none',
        write_raw_finding('### e3'),
        f'## Round 4 · 2026-11-24 · {HEAD}',
        write_raw_finding('### e4'),
    )

    @pytest.fixture
    def harness(self, framed_harness: CaseHarness) -> CaseHarness:
        text = '\n'.join((write_case_text(create_case()), *self.rounds))
        framed_harness.repository.write(CASE_FILE, text)
        return framed_harness

    def test_findings_take_round_day_and_head_from_their_heading(
        self, harness: CaseHarness
    ) -> None:
        stamps = [
            (finding.finding_id, finding.round, finding.at, finding.head)
            for finding in harness.findings
        ]

        assert stamps == [
            ('e1', 2, date(2026, 11, 22), 'abc1234'),
            ('e2', 2, date(2026, 11, 22), 'abc1234'),
            ('e3', 3, date(2026, 11, 23), None),
            ('e4', 4, date(2026, 11, 24), HEAD),
        ]

    def test_numbering_runs_on_across_rounds(self, harness: CaseHarness) -> None:
        assert harness.find_problems() == ()


class TestNumbering:
    @pytest.fixture
    def harness(self, framed_harness: CaseHarness) -> CaseHarness:
        return framed_harness

    @numbering_cases()
    def test_findings_are_numbered_from_one_without_a_gap(
        self, harness: CaseHarness, case: NumberingCase
    ) -> None:
        harness.seed(
            None, *(create_finding(finding_number=finding_number) for finding_number in case.seqs)
        )

        problems = harness.find_problems()

        found = [
            (p.location.finding_id, p.expected) for p in problems if isinstance(p, NumberingError)
        ]
        assert found == list(case.faults)

    def test_each_file_counts_its_own_findings(self, harness: CaseHarness) -> None:
        harness.seed(None, create_finding(finding_number=1), create_finding(finding_number=2))
        harness.seed('T1', create_finding(finding_number=1))
        harness.seed('T10', create_finding(finding_number=1), create_finding(finding_number=2))

        finding_ids = sorted(finding.finding_id for finding in harness.findings)

        assert harness.find_problems() == ()
        assert finding_ids == ['T1.e1', 'T10.e1', 'T10.e2', 'e1', 'e2']


class TestHeadingLayout:
    @pytest.fixture
    def harness(self, framed_harness: CaseHarness) -> CaseHarness:
        return framed_harness

    @layout_cases()
    def test_unreadable_heading_is_named_by_its_line(
        self, harness: CaseHarness, case: LayoutCase
    ) -> None:
        harness.repository.write('threads/T1.md', case.text)

        problems = harness.find_problems()

        assert tuple(map(type, problems)) == (case.error_type,)
        assert str(problems[0]).startswith(case.place)

    @layout_cases()
    def test_unreadable_heading_stops_the_case_from_loading(
        self, harness: CaseHarness, case: LayoutCase
    ) -> None:
        harness.repository.write('threads/T1.md', case.text)

        with pytest.raises(MalformedCaseError):
            harness.casefile.load()
