"""Days, and whole-second UTC moments, the way a clock or a case file holds them."""

from datetime import UTC
from typing import TYPE_CHECKING

from hypothesis import strategies as st

if TYPE_CHECKING:
    from datetime import datetime


def drop_microseconds(moment: datetime) -> datetime:
    return moment.replace(microsecond=0)


days = st.dates()
moments = st.datetimes(timezones=st.just(UTC)).map(drop_microseconds)
