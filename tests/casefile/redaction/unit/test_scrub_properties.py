"""Scrubbing: plain text passes through, each planted secret family is replaced and counted."""

import string
from operator import attrgetter
from typing import TYPE_CHECKING

import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from red_thread_core.redaction import create_secret_patterns

from tests.casefile.redaction.strategies import FAMILIES, planted_secrets

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet
    from red_thread_core.redaction import Redaction

    from tests.casefile.redaction.strategies import Family, Planted


def scrub(text: str) -> Redaction:
    return create_secret_patterns().scrub(text)


def secret_family_cases() -> pytest.MarkDecorator:
    params: list[ParameterSet] = [pytest.param(family, id=family.name) for family in FAMILIES]
    return pytest.mark.parametrize('family', params)


class TestScrubProperties:
    prose = st.text(alphabet=string.ascii_lowercase + ' \n', max_size=60)
    secret_texts = st.builds(attrgetter('whole'), planted_secrets)
    salted_texts = st.builds(
        ' '.join, st.lists(st.one_of(st.text(max_size=20), secret_texts), max_size=5)
    )
    placements = st.lists(st.tuples(prose, planted_secrets), min_size=1, max_size=4)

    @given(text=prose)
    def test_text_holding_no_secret_is_returned_unchanged_with_zero_hits(self, text: str) -> None:
        result = scrub(text)

        assert (result.text, result.hits) == (text, 0)

    @given(text=st.text(max_size=80))
    def test_the_text_changes_exactly_when_something_was_hit(self, text: str) -> None:
        result = scrub(text)

        assert (result.hits == 0) == (result.text == text)

    @given(text=salted_texts)
    def test_scrubbing_twice_gives_the_text_scrubbing_once_gave(self, text: str) -> None:
        once = scrub(text)

        assert scrub(once.text).text == once.text

    @pytest.mark.regression
    @given(text=salted_texts)
    @example(text='see https://alice:hunter2@host.example/path now')
    def test_scrubbing_redacted_text_again_counts_no_hit(self, text: str) -> None:
        once = scrub(text)

        assert scrub(once.text).hits == 0

    @secret_family_cases()
    @given(data=st.data())
    def test_a_planted_secret_of_the_family_is_replaced_and_counted_once(
        self, family: Family, data: st.DataObject
    ) -> None:
        planted = data.draw(family.planted)
        before = data.draw(self.prose)
        after = data.draw(self.prose)

        result = scrub(f'{before} {planted.whole} {after}')

        assert result.text == f'{before} {planted.redacted} {after}'
        assert result.hits == 1

    @given(located=placements)
    def test_hits_count_exactly_the_secrets_planted(
        self, located: list[tuple[str, Planted]]
    ) -> None:
        text = ' '.join(f'{filler} {planted.whole}' for filler, planted in located)
        expected = ' '.join(f'{filler} {planted.redacted}' for filler, planted in located)

        result = scrub(text)

        assert result.text == expected
        assert result.hits == len(located)
