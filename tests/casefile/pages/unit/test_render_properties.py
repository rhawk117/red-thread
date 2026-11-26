"""Page rendering: escaped text, nested templates and tuples, code spans and the page assets."""

import re
from html import escape, unescape
from typing import TYPE_CHECKING

import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from red_thread_core.packaged import read_asset
from red_thread_core.writers.markup import render, render_value

from tests.casefile.pages.asset_names import ASSET_NAMES
from tests.casefile.writers.reading import render_marked_up

if TYPE_CHECKING:
    from red_thread_core.packaged import CoreAsset

BARE_AMPERSAND = re.compile(r'&(?!(?:amp|lt|gt|quot|#x27);)')
METACHARACTERS = '<>"\''
plain = st.text(
    alphabet=st.characters(blacklist_categories=('Cs',), blacklist_characters='`'), max_size=30
)


def asset_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('name', [pytest.param(name, id=name) for name in ASSET_NAMES])


@given(text=st.text(max_size=60))
@example(text='<script>alert("x")</script> & \'quoted\' &lt;')
def test_render_value_escapes_every_html_metacharacter_in_any_text(text: str) -> None:
    rendered = render_value(text)

    assert not any(character in rendered for character in METACHARACTERS)
    assert not BARE_AMPERSAND.search(rendered)
    assert unescape(rendered) == text
    assert rendered == escape(text)


@given(value=st.one_of(st.integers(), st.booleans(), st.none()))
def test_render_value_writes_other_values_as_their_text(value: object) -> None:
    assert render_value(value) == str(value)


@given(first=st.text(max_size=20), second=st.text(max_size=20), third=st.text(max_size=20))
def test_nested_templates_and_tuples_render_as_the_concatenation_of_their_parts(
    first: str, second: str, third: str
) -> None:
    inner = t'<i>{second}</i>'
    outer = t'<b>{first}</b>{(inner, third)}'

    rendered = render(outer)

    expected = f'<b>{escape(first)}</b><i>{escape(second)}</i>{escape(third)}'
    assert rendered == expected
    assert render_value(outer) == expected


@given(parts=st.lists(st.text(max_size=15), max_size=6))
def test_a_tuple_renders_each_member_in_order_and_nested_tuples_flatten(parts: list[str]) -> None:
    flat = ''.join(escape(part) for part in parts)

    assert render_value(tuple(parts)) == flat
    assert render_value((tuple(parts), (tuple(parts),))) == flat * 2


@given(text=st.text(max_size=20))
def test_a_conversion_is_applied_before_the_text_is_escaped(text: str) -> None:
    assert render(t'<p>{text!r}</p>') == f'<p>{escape(repr(text))}</p>'


@given(text=plain)
def test_text_without_a_backtick_marks_up_as_itself(text: str) -> None:
    assert render_marked_up(text) == escape(text)


@given(before=plain, code=plain.filter(bool), after=plain)
@example(before='run ', code='make test', after=' now')
def test_a_code_span_becomes_a_code_element_around_its_escaped_text(
    before: str, code: str, after: str
) -> None:
    rendered = render_marked_up(f'{before}`{code}`{after}')

    assert rendered == f'{escape(before)}<code>{escape(code)}</code>{escape(after)}'


@given(before=plain, after=plain)
def test_a_lone_backtick_stays_literal_text(before: str, after: str) -> None:
    text = f'{before}`{after}'

    assert render_marked_up(text) == escape(text)


@asset_cases()
def test_each_page_asset_has_text(name: CoreAsset) -> None:
    assert read_asset(name).strip()
