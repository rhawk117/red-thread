"""A line's inline markup: code spans become code elements and the rest is escaped text."""

from html import escape
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_core.packaged import read_asset

from tests.casefile.pages.asset_names import ASSET_NAMES
from tests.casefile.writers.reading import render_marked_up

if TYPE_CHECKING:
    from red_thread_core.packaged import CoreAsset

RAW_CHARACTERS = '<>"\''
text_characters = st.characters(exclude_characters='`')
plain_text = st.text(text_characters)
code_text = st.text(text_characters, min_size=1)


def create_marked_up(plain: str, code: str) -> str:
    return f'{plain}`{code}`'


def asset_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('name', [pytest.param(name, id=name) for name in ASSET_NAMES])


class TestInlineMarkup:
    plain_runs = st.lists(st.tuples(plain_text, code_text), max_size=4)

    def test_a_code_span_becomes_a_code_element(self) -> None:
        assert render_marked_up('see `time.sleep` here') == 'see <code>time.sleep</code> here'

    def test_text_inside_a_code_span_is_escaped(self) -> None:
        assert render_marked_up('`<b>&`') == '<code>&lt;b&gt;&amp;</code>'

    def test_text_outside_a_code_span_is_escaped(self) -> None:
        assert render_marked_up('a < b `c`') == 'a &lt; b <code>c</code>'

    def test_a_single_backtick_stays_as_text(self) -> None:
        assert render_marked_up('a `b') == 'a `b'

    def test_empty_text_renders_nothing(self) -> None:
        assert render_marked_up('') == ''

    @given(text=plain_text)
    def test_text_with_no_code_span_renders_as_the_escaped_text(self, text: str) -> None:
        assert render_marked_up(text) == escape(text)

    @given(runs=plain_runs, tail=plain_text)
    def test_every_code_span_is_one_code_element_and_the_rest_is_text(
        self, runs: list[tuple[str, str]], tail: str
    ) -> None:
        text = ''.join(create_marked_up(plain, code) for plain, code in runs) + tail
        expected = ''.join(f'{escape(plain)}<code>{escape(code)}</code>' for plain, code in runs)

        assert render_marked_up(text) == expected + escape(tail)


class TestAssets:
    @asset_cases()
    def test_an_asset_is_read_as_text(self, name: CoreAsset) -> None:
        assert read_asset(name).strip()
