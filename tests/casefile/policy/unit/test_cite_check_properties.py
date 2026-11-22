"""CiteCheck: ok, moved, changed or missing for any quote, line and file, and never an error."""

import string
from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.policy import CiteCheck

if TYPE_CHECKING:
    from red_thread_casefile.policy import CiteState

NOT_FOUND = 'ABSENT'


def number_lines(texts: list[str]) -> tuple[str, ...]:
    return tuple(f'#{number:03d} {text}' for number, text in enumerate(texts, 1))


class TestCiteCheck:
    texts = st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=10)
    files = st.builds(number_lines, st.lists(texts, min_size=2, max_size=30))
    out_of_range = st.one_of(st.integers(max_value=0), st.integers(min_value=31))
    file_lines = st.one_of(st.none(), st.lists(st.text(alphabet='ab ', max_size=6), max_size=8))
    quotes = st.text(alphabet='ab', min_size=1, max_size=3)

    def expect(
        self, quote: str, line: int, lines: list[str] | None
    ) -> tuple[CiteState, int | None]:
        if lines is None:
            return ('missing', None)

        held = [n for n, text in enumerate(lines, 1) if quote in ' '.join(text.split())]
        if line in held:
            return ('ok', None)

        if held:
            return ('moved', held[0])

        if 1 <= line <= len(lines):
            return ('changed', None)

        return ('missing', None)

    @given(lines=files, data=st.data())
    def test_a_quote_equal_to_the_cited_line_is_ok_however_the_line_is_padded(
        self, lines: tuple[str, ...], data: st.DataObject
    ) -> None:
        line = data.draw(st.integers(min_value=1, max_value=len(lines)))
        padded = tuple(f'  {text}\t' for text in lines)

        check = CiteCheck(quote=lines[line - 1], line=line, lines=padded)

        assert (check.get_state(), check.moved_to) == ('ok', None)

    @given(lines=files, data=st.data())
    def test_a_quote_on_exactly_one_other_line_is_moved_to_that_line(
        self, lines: tuple[str, ...], data: st.DataObject
    ) -> None:
        line = data.draw(st.integers(min_value=1, max_value=len(lines)))
        found = data.draw(st.integers(min_value=1, max_value=len(lines)).filter(line.__ne__))

        check = CiteCheck(quote=lines[found - 1], line=line, lines=lines)

        assert (check.get_state(), check.moved_to) == ('moved', found)

    @given(lines=files, data=st.data())
    def test_a_quote_on_no_line_is_changed_when_the_cited_line_exists(
        self, lines: tuple[str, ...], data: st.DataObject
    ) -> None:
        line = data.draw(st.integers(min_value=1, max_value=len(lines)))

        check = CiteCheck(quote=NOT_FOUND, line=line, lines=lines)

        assert (check.get_state(), check.moved_to) == ('changed', None)

    @given(lines=files, line=out_of_range)
    def test_a_quote_on_no_line_is_missing_when_the_cited_line_does_not_exist(
        self, lines: tuple[str, ...], line: int
    ) -> None:
        check = CiteCheck(quote=NOT_FOUND, line=line, lines=lines)

        assert (check.get_state(), check.moved_to) == ('missing', None)

    @given(quote=quotes, line=st.integers())
    def test_a_file_that_cannot_be_read_is_missing_whatever_the_quote_and_line(
        self, quote: str, line: int
    ) -> None:
        check = CiteCheck(quote=quote, line=line, lines=None)

        assert (check.get_state(), check.moved_to) == ('missing', None)

    @given(quote=quotes, line=st.integers(min_value=-3, max_value=12), lines=file_lines)
    def test_the_state_follows_where_the_quote_sits_for_any_line_number(
        self, quote: str, line: int, lines: list[str] | None
    ) -> None:
        expected = self.expect(quote, line, lines)

        check = CiteCheck(quote=quote, line=line, lines=None if lines is None else tuple(lines))

        assert (check.get_state(), check.moved_to) == expected
