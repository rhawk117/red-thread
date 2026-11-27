"""Page rendering: code spans in a line and the page assets."""

import re
from html import escape
from typing import TYPE_CHECKING

import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from red_thread_core.packaged import read_asset

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
