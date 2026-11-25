"""Lines: text split into plain runs and code spans once, when the tree is built."""

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.documents import Code, Link, Text, parse_line, parse_value

from tests.casefile.documents.reading import join_line, write_back


class TestParseLine:
    texts = st.text(alphabet=st.sampled_from('ab `\n<&'), max_size=40) | st.text()

    @given(text=texts)
    def test_joining_the_line_back_gives_the_text(self, text: str) -> None:
        assert join_line(parse_line(text)) == text

    @given(text=texts)
    def test_no_node_is_empty(self, text: str) -> None:
        assert all(map(write_back, parse_line(text)))

    def test_a_backtick_pair_becomes_a_code_span(self) -> None:
        expected = (Text(value='run '), Code(value='make check'), Text(value=' first'))

        assert parse_line('run `make check` first') == expected

    def test_an_unpaired_backtick_stays_plain(self) -> None:
        assert parse_line('a ` b') == (Text(value='a ` b'),)

    def test_empty_text_is_an_empty_line(self) -> None:
        assert parse_line('') == ()


class TestParseValue:
    url = 'https://example.invalid/docs'

    def test_a_url_is_one_link(self) -> None:
        assert parse_value(self.url) == (Link(url=self.url),)

    def test_other_text_is_a_line(self) -> None:
        assert parse_value('see `x`') == parse_line('see `x`')
