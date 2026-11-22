"""Framing a case over memory fakes: its id, its record and its refusal to reuse a case."""

import re
from dataclasses import replace
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.domain import build_case_id
from red_thread_casefile.errors import CaseExistsError
from red_thread_casefile.services import Framing
from red_thread_casefile.store import SystemClock

from tests.casefile.framing.cases import case_id_params, language_params
from tests.casefile.ledger.builders import create_case_harness
from tests.casefile.ledger.memory import HEAD, MOMENT

if TYPE_CHECKING:
    from datetime import date

    from tests.casefile.framing.cases import CaseIdCase, LanguageCase
    from tests.casefile.ledger.builders import CaseHarness

CASE_ID_SHAPE = re.compile(r'\d{8}(-[a-z0-9]+){0,5}')


def make_timestamp(day: date) -> str:
    return f'{day.isoformat()}T10:00:00+00:00'


def case_id_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', case_id_params())


def language_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', language_params())


class TestCaseId:
    days = st.dates().map(make_timestamp)
    labels = st.text(max_size=120)

    @case_id_cases()
    def test_id_is_the_utc_date_and_the_leading_words(self, case: CaseIdCase) -> None:
        assert build_case_id(case.created, case.label) == case.expected

    @given(created=days, label=labels)
    def test_id_is_a_date_and_at_most_five_lowercase_words(self, created: str, label: str) -> None:
        case_id = build_case_id(created, label)

        assert CASE_ID_SHAPE.fullmatch(case_id)
        assert case_id.startswith(created[:10].replace('-', ''))

    def test_system_clock_stamps_utc(self) -> None:
        stamped = datetime.fromisoformat(SystemClock().now())

        assert stamped.utcoffset() == timedelta(0)


class TestFrame:
    framing = Framing(
        id='20261121-retry-queue-slowdown',
        target='why the retry queue stalls',
        kind='root-cause',
        bar='name the line that stalls it',
        publish=True,
    )

    def test_framed_case_records_its_framing_the_time_and_the_head(
        self, case_harness: CaseHarness
    ) -> None:
        case = case_harness.casefile.frame(self.framing)

        assert case_harness.repository.read_case() == case
        assert (case.id, case.target, case.kind, case.bar, case.publish) == (
            self.framing.id,
            self.framing.target,
            'root-cause',
            self.framing.bar,
            True,
        )
        assert (case.created, case.head) == (MOMENT, HEAD)

    def test_case_framed_in_a_tree_with_no_commit_has_no_head(
        self, case_harness: CaseHarness
    ) -> None:
        case_harness.tree.advance(None)

        assert case_harness.casefile.frame(self.framing).head is None

    def test_existing_case_is_refused_and_left_as_it_was(self, case_harness: CaseHarness) -> None:
        first = case_harness.casefile.frame(self.framing)

        with pytest.raises(CaseExistsError) as raised:
            case_harness.casefile.frame(replace(self.framing, target='something else'))

        assert raised.value.case_id == self.framing.id
        assert case_harness.repository.read_case() == first
        assert case_harness.entries == ()

    def test_case_file_directory_is_excluded_from_git_once_per_new_case(
        self, case_harness: CaseHarness
    ) -> None:
        case_harness.casefile.frame(self.framing)
        with pytest.raises(CaseExistsError):
            case_harness.casefile.frame(self.framing)

        assert case_harness.tree.exclusions == ['.red-thread/']

    @language_cases()
    def test_languages_are_ranked_by_file_count(
        self, case_harness: CaseHarness, case: LanguageCase
    ) -> None:
        case_harness.tree.files.clear()
        case_harness.tree.files.update(dict.fromkeys(case.files, ()))

        recorded = case_harness.casefile.frame(self.framing).capabilities

        assert recorded.languages == case.languages

    def test_navigation_tool_is_recorded_when_installed(self) -> None:
        harness = create_case_harness(tools=frozenset({'agentlens'}))

        assert harness.casefile.frame(self.framing).capabilities.navigation_tool

    def test_navigation_tool_is_recorded_as_missing_when_not_installed(
        self, case_harness: CaseHarness
    ) -> None:
        assert not case_harness.casefile.frame(self.framing).capabilities.navigation_tool
