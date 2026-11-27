"""The element builder: each call returns a new element, every value is escaped, and the layout."""

from html import unescape

import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from red_thread_core.elements import blank_unsafe_url, element, render_fragment

METACHARACTERS = '<>"\''


def unsafe_url_cases() -> pytest.MarkDecorator:
    urls = {
        'javascript': 'javascript:alert(1)',
        'upper-case': 'JavaScript:alert(1)',
        'leading-space': ' javascript:alert(1)',
        'tab-inside': 'java\tscript:alert(1)',
        'data': 'data:text/html,x',
    }
    return pytest.mark.parametrize(
        'url', [pytest.param(url, id=name) for name, url in urls.items()]
    )


def safe_url_cases() -> pytest.MarkDecorator:
    urls = {
        'https': 'https://example.invalid/a?b=1',
        'http': 'http://example.invalid',
        'relative': '../plans/p1/plan.html',
        'anchor': '#section-a',
        'colon-in-path': 'notes/a:b',
    }
    return pytest.mark.parametrize(
        'url', [pytest.param(url, id=name) for name, url in urls.items()]
    )


class TestBuilding:
    def test_a_call_returns_a_new_element_and_leaves_the_first_unchanged(self) -> None:
        bare = element('p')

        built = bare.with_attributes({'class': 'claim'}).set_text('a')

        assert bare.render() == '<p></p>'
        assert built.render() == '<p class="claim">a</p>'

    def test_nest_keeps_the_order_and_skips_none(self) -> None:
        built = element('p').nest('a', None, element('code').set_text('b'), 'c')

        assert built.render() == '<p>a<code>b</code>c</p>'

    def test_set_text_replaces_the_children(self) -> None:
        assert element('p').nest('a', 'b').set_text(3).render() == '<p>3</p>'

    def test_true_is_a_bare_attribute_and_none_and_false_are_left_out(self) -> None:
        marks = {'open': True, 'hidden': False, 'data-kind': None, 'id': 'x'}

        assert (
            element('details').with_attributes(marks).render() == '<details open id="x"></details>'
        )


class TestEscaping:
    @given(text=st.text(max_size=60))
    @example(text='<script>alert("x")</script> & \'q\'')
    def test_text_is_shown_as_text_and_never_as_markup(self, text: str) -> None:
        inner = element('p').set_text(text).render().removeprefix('<p>').removesuffix('</p>')

        assert not set(METACHARACTERS) & set(inner)
        assert unescape(inner) == text

    @given(value=st.text(max_size=60))
    def test_an_attribute_value_cannot_leave_its_quotes(self, value: str) -> None:
        rendered = element('p').with_attributes({'title': value}).render()

        written = rendered.removeprefix('<p title="').removesuffix('"></p>')
        assert '"' not in written
        assert unescape(written) == value


class TestLinks:
    @unsafe_url_cases()
    def test_a_link_that_is_not_to_the_web_keeps_its_text_and_loses_its_target(
        self, url: str
    ) -> None:
        link = element('a').with_attributes({'href': url}).set_text('docs')

        assert link.render() == '<a href="">docs</a>'

    @safe_url_cases()
    def test_a_web_or_relative_link_keeps_its_target(self, url: str) -> None:
        assert blank_unsafe_url(url) == url


class TestLayout:
    def test_an_element_of_blocks_puts_each_child_on_its_own_indented_line(self) -> None:
        items = element('ul').nest(element('li').set_text('a'), element('li').set_text('b'))

        rendered = element('div').nest(items).render()

        assert rendered == '<div>\n  <ul>\n    <li>a</li>\n    <li>b</li>\n  </ul>\n</div>'

    def test_an_element_holding_text_stays_on_one_line(self) -> None:
        rendered = element('p').nest('see ', element('div').set_text('x')).render()

        assert rendered == '<p>see <div>x</div></p>'

    def test_side_by_side_phrasing_elements_stay_on_one_line(self) -> None:
        buttons = (element('button').set_text('a'), element('button').set_text('b'))

        rendered = element('div').nest(*buttons).render()

        assert rendered == '<div><button>a</button><button>b</button></div>'

    def test_a_lone_phrasing_child_stays_on_its_parents_line(self) -> None:
        rendered = element('li').nest(element('time').set_text('2026-11-27')).render()

        assert rendered == '<li><time>2026-11-27</time></li>'

    def test_a_pre_keeps_its_content_exactly(self) -> None:
        listing = element('pre').nest(element('code').set_text('a\n  b'))

        assert listing.render(depth=2) == '<pre><code>a\n  b</code></pre>'

    def test_a_fragment_writes_each_element_on_its_own_line_and_skips_none(self) -> None:
        assert render_fragment((element('p'), None, element('ol'))) == '<p></p>\n<ol></ol>\n'
