"""The page's template renderer escapes every value and leaves the template's own markup alone."""

from html import escape, unescape
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.assets import read_asset
from red_thread_casefile.pages import mark_up, render, render_part, render_value

from tests.casefile.pages.asset_names import ASSET_NAMES

if TYPE_CHECKING:
    from string.templatelib import Template

    from red_thread_casefile.assets import AssetName

RAW_CHARACTERS = '<>"\''
text_characters = st.characters(exclude_characters='`')
plain_text = st.text(text_characters)
code_text = st.text(text_characters, min_size=1)


def create_marked_up(plain: str, code: str) -> str:
    return f'{plain}`{code}`'


def render_all(templates: tuple[Template, ...]) -> str:
    return ''.join(map(render, templates))


def asset_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('name', [pytest.param(name, id=name) for name in ASSET_NAMES])


class TestRenderValue:
    texts = st.text()
    scalars = st.integers() | st.floats(allow_nan=False) | st.booleans() | st.none()
    text_tuples = st.lists(st.text(), max_size=5).map(tuple)

    @given(text=texts)
    def test_text_is_shown_as_text_and_never_as_markup(self, text: str) -> None:
        rendered = render_value(text)

        assert not set(RAW_CHARACTERS) & set(rendered)
        assert unescape(rendered) == text

    @given(value=scalars)
    def test_a_value_that_is_not_text_is_shown_as_its_text(self, value: object) -> None:
        assert unescape(render_value(value)) == str(value)

    @given(texts=text_tuples)
    def test_a_tuple_is_the_concatenation_of_its_parts(self, texts: tuple[str, ...]) -> None:
        rendered = render_value(texts)

        assert not set(RAW_CHARACTERS) & set(rendered)
        assert unescape(rendered) == ''.join(texts)

    @given(text=texts)
    def test_a_nested_template_keeps_its_markup_and_escapes_its_values(self, text: str) -> None:
        rendered = render_value(t'<i>{text}</i>')

        assert rendered.startswith('<i>')
        assert rendered.endswith('</i>')
        assert unescape(rendered.removeprefix('<i>').removesuffix('</i>')) == text

    def test_a_template_inside_a_tuple_keeps_its_markup(self) -> None:
        assert render_value((t'<b>{"x < y"}</b>', 'a & b')) == '<b>x &lt; y</b>a &amp; b'

    def test_an_empty_tuple_renders_nothing(self) -> None:
        assert render_value(()) == ''


class TestRender:
    texts = st.text()

    @given(text=texts)
    def test_the_template_text_is_kept_and_the_value_is_escaped(self, text: str) -> None:
        rendered = render(t'<p class="claim">{text}</p>')

        assert rendered.startswith('<p class="claim">')
        assert rendered.endswith('</p>')
        inner = rendered.removeprefix('<p class="claim">').removesuffix('</p>')
        assert not set(RAW_CHARACTERS) & set(inner)
        assert unescape(inner) == text

    def test_a_template_with_no_value_is_returned_as_written(self) -> None:
        assert render(t'<br>') == '<br>'

    def test_a_conversion_is_applied_before_the_value_is_escaped(self) -> None:
        text = '<a>'

        assert render(t'{text!r}') == escape(repr(text))

    def test_a_literal_ampersand_in_the_template_is_not_escaped_again(self) -> None:
        assert render(t'&amp;{"&"}') == '&amp;&amp;'

    def test_an_interpolation_is_escaped_and_a_literal_part_is_not(self) -> None:
        template = t'<{"<"}>'
        literal, value, closing = template

        assert render_part(literal) == '<'
        assert render_part(value) == '&lt;'
        assert render_part(closing) == '>'


class TestMarkUp:
    plain_runs = st.lists(st.tuples(plain_text, code_text), max_size=4)

    def test_a_code_span_becomes_a_code_element(self) -> None:
        assert render_all(mark_up('see `time.sleep` here')) == 'see <code>time.sleep</code> here'

    def test_text_inside_a_code_span_is_escaped(self) -> None:
        assert render_all(mark_up('`<b>&`')) == '<code>&lt;b&gt;&amp;</code>'

    def test_text_outside_a_code_span_is_escaped(self) -> None:
        assert render_all(mark_up('a < b `c`')) == 'a &lt; b <code>c</code>'

    def test_a_single_backtick_stays_as_text(self) -> None:
        assert render_all(mark_up('a `b')) == 'a `b'

    def test_empty_text_renders_nothing(self) -> None:
        assert render_all(mark_up('')) == ''

    @given(text=plain_text)
    def test_text_with_no_code_span_renders_as_the_escaped_text(self, text: str) -> None:
        assert render_all(mark_up(text)) == escape(text)

    @given(runs=plain_runs, tail=plain_text)
    def test_every_code_span_is_one_code_element_and_the_rest_is_text(
        self, runs: list[tuple[str, str]], tail: str
    ) -> None:
        text = ''.join(create_marked_up(plain, code) for plain, code in runs) + tail
        expected = ''.join(f'{escape(plain)}<code>{escape(code)}</code>' for plain, code in runs)

        assert render_all(mark_up(text)) == expected + escape(tail)


class TestAssets:
    @asset_cases()
    def test_an_asset_is_read_as_text(self, name: AssetName) -> None:
        assert read_asset(name).strip()
