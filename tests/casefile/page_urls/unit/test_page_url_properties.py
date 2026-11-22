"""get_page_problem: only an https link without whitespace is a page url."""

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.errors import InvalidPageUrlError
from red_thread_casefile.policy import get_page_problem

WHITESPACE = ' \t\n\r\x0b\x0c\x1c\x85\N{NO-BREAK SPACE}\N{LINE SEPARATOR}\N{PARAGRAPH SEPARATOR}'
SCHEMES = ('http://', 'ftp://', 'HTTPS://', 'file://', '')


def add_scheme(scheme: str, rest: str) -> str:
    return f'{scheme}x{rest}'


class TestGetPageProblem:
    solid = st.text(
        alphabet=st.characters(blacklist_categories=('Cs', 'Cc', 'Zs', 'Zl', 'Zp')), max_size=40
    )
    gaps = st.sampled_from(WHITESPACE)
    other_schemes = st.builds(add_scheme, st.sampled_from(SCHEMES), solid)

    @given(rest=solid)
    def test_an_https_link_without_whitespace_is_a_page_url(self, rest: str) -> None:
        assert get_page_problem(f'https://{rest}') is None

    @given(url=other_schemes)
    def test_a_link_that_is_not_https_is_rejected_with_the_url(self, url: str) -> None:
        problem = get_page_problem(url)

        assert isinstance(problem, InvalidPageUrlError)
        assert problem.url == url

    @given(left=solid, gap=gaps, right=solid)
    def test_an_https_link_with_any_whitespace_is_rejected_with_the_url(
        self, left: str, gap: str, right: str
    ) -> None:
        url = f'https://{left}{gap}{right}'

        problem = get_page_problem(url)

        assert isinstance(problem, InvalidPageUrlError)
        assert problem.url == url
