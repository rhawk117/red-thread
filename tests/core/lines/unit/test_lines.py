"""Text as numbered lines: how it splits, numbers, cuts at marks and trims."""

import pytest
from red_thread_core.lines import Cut, Cuts, Line, cut_at, number_lines, split_lines, trim


class TestSplitLines:
    @pytest.mark.parametrize(
        ('text', 'lines'),
        [
            pytest.param('', [], id='empty'),
            pytest.param('a\nb\n', ['a', 'b'], id='trailing-newline-dropped'),
            pytest.param('a\r\n\r\nb', ['a', '', 'b'], id='crlf-folded'),
            pytest.param('a\n\nb', ['a', '', 'b'], id='blank-line-kept'),
        ],
    )
    def test_splits_on_newlines(self, text: str, lines: list[str]) -> None:
        assert split_lines(text) == lines


class TestNumberLines:
    def test_numbers_from_the_given_start(self) -> None:
        assert number_lines(['x', 'y'], 4) == (Line(number=4, text='x'), Line(number=5, text='y'))


class TestLineMarks:
    def test_blank_line_is_whitespace_only(self) -> None:
        assert Line(number=1, text='  \t').is_blank

    def test_mark_is_the_stripped_text(self) -> None:
        assert Line(number=1, text='  ## Goal  ').mark == '## Goal'


class TestCutAt:
    lines = number_lines(['intro', '# A', 'a1', '# B', 'b1', 'b2'], 1)

    def test_text_before_the_first_mark_is_the_preamble(self) -> None:
        assert cut_at(self.lines, '# ').preamble == self.lines[:1]

    def test_each_mark_opens_a_part_running_to_the_next_mark(self) -> None:
        cuts = cut_at(self.lines, '# ')

        assert cuts.parts == (
            Cut(head=self.lines[1], body=self.lines[2:3]),
            Cut(head=self.lines[3], body=self.lines[4:]),
        )

    def test_no_mark_leaves_every_line_in_the_preamble(self) -> None:
        assert cut_at(self.lines, '## ') == Cuts(preamble=self.lines, parts=())


class TestTrim:
    @pytest.mark.parametrize(
        ('texts', 'kept'),
        [
            pytest.param(['', 'a', '', 'b', ''], ['a', '', 'b'], id='blank-edges-dropped'),
            pytest.param(['  ', '\t'], [], id='all-blank'),
            pytest.param(['a'], ['a'], id='single-line'),
        ],
    )
    def test_drops_blank_edges_and_keeps_inner_blanks(
        self, texts: list[str], kept: list[str]
    ) -> None:
        assert [line.text for line in trim(number_lines(texts, 1))] == kept
