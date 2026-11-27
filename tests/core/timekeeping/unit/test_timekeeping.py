"""The clock, the day and moment text a case file holds, and the deadline a parse runs under."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from red_thread_core.timekeeping import (
    Clock,
    SystemClock,
    read_day,
    start_deadline,
    write_compact_day,
    write_moment,
)

from tests.core.timekeeping.clock import DAY, DAY_TEXT, MOMENT, MOMENT_TEXT
from tests.core.timekeeping.strategies import days, moments

if TYPE_CHECKING:
    from datetime import date


def unreadable_day_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        'text',
        [
            pytest.param('2026-13-01', id='month-thirteen'),
            pytest.param('2026-11-21T09:30:00', id='a-moment'),
            pytest.param('yesterday', id='words'),
            pytest.param('', id='empty'),
        ],
    )


class TestSystemClock:
    def test_now_is_a_whole_second_in_utc_between_two_readings(self) -> None:
        before = datetime.now(UTC).replace(microsecond=0)
        stamped = SystemClock().now()
        after = datetime.now(UTC)

        assert before <= stamped <= after
        assert (stamped.tzinfo, stamped.microsecond) == (UTC, 0)

    def test_the_system_clock_is_a_clock(self) -> None:
        assert isinstance(SystemClock(), Clock)


class TestMomentText:
    def test_a_moment_is_written_to_the_second_with_its_offset(self) -> None:
        assert write_moment(MOMENT) == MOMENT_TEXT

    @given(moment=moments)
    def test_a_written_moment_reads_back_as_the_same_moment(self, moment: datetime) -> None:
        assert datetime.fromisoformat(write_moment(moment)) == moment


class TestDayText:
    def test_a_compact_day_drops_the_dashes(self) -> None:
        assert write_compact_day(DAY) == DAY_TEXT.replace('-', '')

    @given(day=days)
    def test_a_compact_day_is_eight_digits_in_calendar_order(self, day: date) -> None:
        written = write_compact_day(day)

        assert (len(written), written.isdigit()) == (8, True)
        assert written == day.isoformat().replace('-', '')

    @given(day=days)
    def test_an_iso_day_reads_back_as_that_day(self, day: date) -> None:
        assert read_day(day.isoformat()) == day

    @unreadable_day_cases()
    def test_text_that_is_not_one_iso_day_reads_as_none(self, text: str) -> None:
        assert read_day(text) is None


class TestDeadline:
    def test_a_deadline_of_no_time_has_expired(self) -> None:
        assert start_deadline(0).is_expired()

    def test_a_deadline_an_hour_away_has_not_expired(self) -> None:
        assert not start_deadline(3600).is_expired()
