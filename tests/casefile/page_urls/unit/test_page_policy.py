"""get_page_problem: which links the board's page may be recorded as."""

from dataclasses import dataclass

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.errors import InvalidPageUrlError
from red_thread_casefile.policy import get_page_problem

from tests.params import as_params

WHITESPACE = (
    ' ',
    '\t',
    '\n',
    '\r',
    '\x0b',
    '\x0c',
    '\N{NO-BREAK SPACE}',
    '\N{EM SPACE}',
    '\N{IDEOGRAPHIC SPACE}',
)


@dataclass(slots=True, kw_only=True, frozen=True)
class UrlScenario:
    name: str
    url: str
    accepted: bool
    marks: tuple[pytest.MarkDecorator, ...] = ()


def page_url_cases() -> pytest.MarkDecorator:
    scenarios = [
        UrlScenario(name='plain-https', url='https://example.invalid/board', accepted=True),
        UrlScenario(
            name='https-with-query-and-fragment',
            url='https://example.invalid/b/9?x=1&y=2#top',
            accepted=True,
        ),
        UrlScenario(name='https-with-port', url='https://example.invalid:8443/b', accepted=True),
        UrlScenario(name='http', url='http://example.invalid/board', accepted=False),
        UrlScenario(name='ftp', url='ftp://example.invalid/board', accepted=False),
        UrlScenario(name='no-scheme', url='example.invalid/board', accepted=False),
        UrlScenario(name='scheme-only-in-the-middle', url='see https://x.invalid', accepted=False),
        UrlScenario(name='javascript', url='javascript:alert(1)', accepted=False),
        UrlScenario(name='empty', url='', accepted=False),
        UrlScenario(name='space-inside', url='https://example.invalid/a b', accepted=False),
        UrlScenario(name='tab-inside', url='https://example.invalid/a\tb', accepted=False),
        UrlScenario(name='newline-inside', url='https://example.invalid/a\nb', accepted=False),
        UrlScenario(name='trailing-newline', url='https://example.invalid/a\n', accepted=False),
        UrlScenario(name='leading-space', url=' https://example.invalid/a', accepted=False),
        UrlScenario(name='trailing-space', url='https://example.invalid/a ', accepted=False),
    ]
    return pytest.mark.parametrize('scenario', as_params(scenarios))


class TestPageUrlPolicy:
    visible = st.text(alphabet=st.characters(exclude_categories=('Cs', 'Z', 'Cc')))
    whitespace = st.sampled_from(WHITESPACE)

    @page_url_cases()
    def test_only_an_https_link_with_no_whitespace_is_accepted(self, scenario: UrlScenario) -> None:
        problem = get_page_problem(scenario.url)

        assert (problem is None) is scenario.accepted
        if problem:
            assert isinstance(problem, InvalidPageUrlError)
            assert problem.url == scenario.url

    @given(tail=visible)
    def test_any_https_link_without_whitespace_is_accepted(self, tail: str) -> None:
        assert not get_page_problem(f'https://{tail}')

    @given(head=visible, gap=whitespace, tail=visible)
    def test_whitespace_anywhere_after_the_scheme_is_rejected(
        self, head: str, gap: str, tail: str
    ) -> None:
        assert isinstance(get_page_problem(f'https://{head}{gap}{tail}'), InvalidPageUrlError)

    @given(
        scheme=st.sampled_from(('http', 'ftp', 'file', 'ssh', 'javascript', 'data')), tail=visible
    )
    def test_any_other_scheme_is_rejected(self, scheme: str, tail: str) -> None:
        assert isinstance(get_page_problem(f'{scheme}://{tail}'), InvalidPageUrlError)
