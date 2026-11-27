"""A clock that always reads one moment, and that moment and its day as values and as text."""

from dataclasses import dataclass
from datetime import UTC, datetime

MOMENT = datetime(2026, 11, 21, 9, 30, tzinfo=UTC)
MOMENT_TEXT = '2026-11-21T09:30:00+00:00'
DAY = MOMENT.date()
DAY_TEXT = '2026-11-21'


@dataclass(slots=True, kw_only=True, frozen=True)
class FixedClock:
    moment: datetime = MOMENT

    def now(self) -> datetime:
        return self.moment
