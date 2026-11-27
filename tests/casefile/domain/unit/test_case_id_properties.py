"""build_case_id: a day and at most five lowercase words, whatever the label holds."""

import re
from typing import TYPE_CHECKING

from hypothesis import example, given
from hypothesis import strategies as st
from red_thread_casefile.domain import build_case_id

from tests.core.timekeeping.clock import MOMENT
from tests.core.timekeeping.strategies import moments

if TYPE_CHECKING:
    from datetime import datetime

SHAPE = re.compile(r'\d{8}(?:-[a-z0-9]+){0,5}')
WORDS = re.compile(r'[a-z0-9]+')


def write_digits(created: datetime) -> str:
    return f'{created.year:04}{created.month:02}{created.day:02}'


class TestBuildCaseId:
    created = moments
    plain_labels = st.text(alphabet='AbCdEf012 -_.,:!', max_size=60)

    @given(created=created, label=st.text(max_size=80))
    @example(created=MOMENT, label='')
    @example(created=MOMENT, label='--  !!  ')
    def test_the_id_is_a_day_then_at_most_five_lowercase_alphanumeric_words(
        self, created: datetime, label: str
    ) -> None:
        assert SHAPE.fullmatch(build_case_id(created, label))

    @given(created=created, label=st.text(max_size=80))
    def test_the_id_starts_with_the_day_the_case_was_created(
        self, created: datetime, label: str
    ) -> None:
        assert build_case_id(created, label).startswith(write_digits(created))

    @given(created=created, label=plain_labels)
    @example(created=MOMENT, label='Why the Retry queue stalls on Monday x y')
    def test_the_words_are_the_first_five_of_the_label_lowercased(
        self, created: datetime, label: str
    ) -> None:
        words = WORDS.findall(label.lower())[:5]

        assert build_case_id(created, label) == '-'.join((write_digits(created), *words))
