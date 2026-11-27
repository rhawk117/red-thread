"""Time in one place: the clock that stamps a record, days and moments as text, and deadlines."""

import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol, runtime_checkable

MOMENT_PRECISION = 'seconds'


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime: ...


@dataclass(slots=True, kw_only=True, frozen=True)
class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC).replace(microsecond=0)


def write_moment(moment: datetime) -> str:
    return moment.isoformat(timespec=MOMENT_PRECISION)


def write_compact_day(day: date) -> str:
    return day.isoformat().replace('-', '')


def read_day(text: str) -> date | None:
    try:
        day = date.fromisoformat(text)
    except ValueError:
        return None
    return day


@dataclass(slots=True, kw_only=True, frozen=True)
class Deadline:
    expires_at: float

    def is_expired(self, *_progress: object) -> bool:
        return time.monotonic() >= self.expires_at


def start_deadline(seconds: float) -> Deadline:
    return Deadline(expires_at=time.monotonic() + seconds)
