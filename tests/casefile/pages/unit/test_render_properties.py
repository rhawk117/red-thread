"""Page rendering: escaped text, code spans, the attribute writer and the web link filter."""

import re
from html import unescape
from typing import TYPE_CHECKING

import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from markupsafe import escape
from red_thread_core.packaged import read_asset
from red_thread_core.writers.markup import keep_safe_url, write_attributes

from tests.casefile.pages.asset_names import ASSET_NAMES
from tests.casefile.writers.reading import render_marked_up

if TYPE_CHECKING:
    from red_thread_core.packaged import CoreAsset

BARE_AMPERSAND = re.compile(r'&(?!(?:amp|lt|gt|#34|#39);)')
METACHARACTERS = '<>"\''
plain = st.text(
    alphabet=st.characters(blacklist_categories=('Cs',), blacklist_characters='`'), max_size=30
)
names = st.from_regex(r'[a-z][a-z-]{0,10}', fullmatch=True)
UNSAFE_SCHEMES = st.sampled_from(('javascript', 'JavaScript', 'data', 'vbscript', 'file'))


def asset_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('name', [pytest.param(name, id=name) for name in ASSET_NAMES])


def escape_text(text: str) -> str:
    return str(escape(text))


@given(text=plain)
@example(text='<script>alert("x")</script> & \'quoted\' &lt;')
def test_text_without_a_backtick_marks_up_as_its_escaped_self(text: str) -> None:
    rendered = render_marked_up(text)

    assert not any(character in rendered for character in METACHARACTERS)
    assert not BARE_AMPERSAND.search(rendered)
    assert unescape(rendered) == text


@given(before=plain, code=plain.filter(bool), after=plain)
@example(before='run ', code='make test', after=' now')
def test_a_code_span_becomes_a_code_element_around_its_escaped_text(
    before: str, code: str, after: str
) -> None:
    rendered = render_marked_up(f'{before}`{code}`{after}')

    assert rendered == f'{escape_text(before)}<code>{escape_text(code)}</code>{escape_text(after)}'


@given(before=plain, after=plain)
def test_a_lone_backtick_stays_literal_text(before: str, after: str) -> None:
    text = f'{before}`{after}'

    assert render_marked_up(text) == escape_text(text)


def test_empty_text_renders_nothing() -> None:
    assert render_marked_up('') == ''


@given(name=names, value=st.text(max_size=20))
def test_an_attribute_value_is_escaped_and_reads_back_as_written(name: str, value: str) -> None:
    written = str(write_attributes({name: value}))

    assert written.startswith(f' {name}="')
    assert unescape(written.removeprefix(f' {name}="').removesuffix('"')) == value
    assert '"' not in written.removeprefix(f' {name}="').removesuffix('"')


def test_a_true_attribute_is_bare_and_a_missing_one_is_left_out() -> None:
    attributes = {'open': True, 'hidden': False, 'data-kind': None, 'id': 'a'}

    assert str(write_attributes(attributes)) == ' open id="a"'


@given(path=st.text(max_size=20))
@example(path='a?b=1&c=2#top')
def test_a_web_url_is_kept_as_it_is(path: str) -> None:
    url = f'https://example.invalid/{path}'

    assert keep_safe_url(url) == url


@pytest.mark.parametrize('url', ['../plans/p1/plan.html', '#section-a', 'notes.md', ''])
def test_a_url_without_a_scheme_is_kept_as_it_is(url: str) -> None:
    assert keep_safe_url(url) == url


@given(scheme=UNSAFE_SCHEMES, rest=st.text(max_size=20))
@example(scheme='javascript', rest='alert(1)')
def test_a_url_with_any_other_scheme_is_dropped(scheme: str, rest: str) -> None:
    assert keep_safe_url(f'{scheme}:{rest}') == ''


@pytest.mark.parametrize(
    'url', [' javascript:alert(1)', 'java\tscript:alert(1)', '\x01javascript:x']
)
def test_a_scheme_hidden_by_whitespace_or_control_characters_is_still_dropped(url: str) -> None:
    assert keep_safe_url(url) == ''


@asset_cases()
def test_each_page_asset_has_text(name: CoreAsset) -> None:
    assert read_asset(name).strip()
