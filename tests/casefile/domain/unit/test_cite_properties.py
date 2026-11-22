"""Cite: path, line and form for relative paths, absolute paths, parent traversal and URLs."""

from hypothesis import example, given
from hypothesis import strategies as st
from red_thread_casefile.domain import Cite


class TestCite:
    segments = st.from_regex(r'[A-Za-z0-9_-][A-Za-z0-9_.-]{0,8}', fullmatch=True)
    path_parts = st.lists(segments, min_size=1, max_size=4)
    lines = st.integers(min_value=1, max_value=10**6)
    schemes = st.sampled_from(('http://', 'https://'))
    zero_lines = st.from_regex(r'0[0-9]{0,3}', fullmatch=True)

    @given(parts=path_parts, line=lines)
    @example(parts=['src', 'queue.py'], line=3)
    def test_a_relative_path_and_line_are_read_back(self, parts: list[str], line: int) -> None:
        cite = Cite(raw=f'{"/".join(parts)}:{line}')

        assert (cite.path, cite.line, cite.form) == ('/'.join(parts), line, 'path')

    @given(parts=path_parts, line=lines, end=lines)
    def test_a_line_range_cites_its_first_line(self, parts: list[str], line: int, end: int) -> None:
        cite = Cite(raw=f'{"/".join(parts)}:{line}-{end}')

        assert (cite.path, cite.line, cite.form) == ('/'.join(parts), line, 'path')

    @given(parts=path_parts, line=lines)
    def test_surrounding_whitespace_is_ignored(self, parts: list[str], line: int) -> None:
        cite = Cite(raw=f' \t{"/".join(parts)}:{line}\n')

        assert (cite.path, cite.line) == ('/'.join(parts), line)

    @given(parts=path_parts, line=lines)
    def test_an_absolute_path_is_neither_a_path_nor_a_line(
        self, parts: list[str], line: int
    ) -> None:
        cite = Cite(raw=f'/{"/".join(parts)}:{line}')

        assert (cite.path, cite.line, cite.form) == (None, None, 'other')

    @given(parts=path_parts, line=lines, data=st.data())
    def test_a_path_through_a_parent_directory_is_neither_a_path_nor_a_line(
        self, parts: list[str], line: int, data: st.DataObject
    ) -> None:
        index = data.draw(st.integers(min_value=0, max_value=len(parts)))
        climbing = [*parts[:index], '..', *parts[index:]]

        cite = Cite(raw=f'{"/".join(climbing)}:{line}')

        assert (cite.path, cite.line, cite.form) == (None, None, 'other')

    @given(scheme=schemes, rest=st.text(max_size=40))
    def test_a_url_is_a_url_with_no_path_and_no_line(self, scheme: str, rest: str) -> None:
        cite = Cite(raw=f'{scheme}{rest}')

        assert (cite.path, cite.line, cite.form) == (None, None, 'url')

    @given(parts=path_parts, line=zero_lines)
    def test_a_line_that_is_zero_or_starts_with_zero_is_not_a_line(
        self, parts: list[str], line: str
    ) -> None:
        cite = Cite(raw=f'{"/".join(parts)}:{line}')

        assert (cite.path, cite.line, cite.form) == (None, None, 'other')

    @given(raw=st.text(max_size=60))
    def test_any_text_has_a_consistent_form(self, raw: str) -> None:
        cite = Cite(raw=raw)

        assert (cite.path is None) == (cite.line is None)
        assert (cite.form == 'path') == (cite.path is not None)
        assert (cite.form == 'url') == raw.startswith(('http://', 'https://'))
