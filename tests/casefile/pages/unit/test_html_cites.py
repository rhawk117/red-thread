"""HtmlWriter: links, copy buttons and code spans."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.documents import Citation
from red_thread_core.documents import PointList, Section, parse_line

from tests.casefile.pages.builders import PLAIN_URL
from tests.casefile.pages.html_reading import (
    find_buttons,
    find_tags,
    list_attribute_names,
    list_cite_blocks,
    list_code_spans,
    list_copy_values,
    list_tag_names,
)
from tests.casefile.writers.builders import create_document, create_entry_node
from tests.casefile.writers.reading import render_page

if TYPE_CHECKING:
    from red_thread_casefile.documents import EntryNode
    from red_thread_core.documents import Document


def create_cited_node(text: str, ref: str, target: str) -> EntryNode:
    return create_entry_node(text, ref).replace_with(citation=Citation(target=target))


def create_point_document(text: str) -> Document:
    points = PointList(points=(parse_line(text),))
    return create_document().replace_with(sections=(Section(title='Findings', blocks=(points,)),))


def non_url_cite_cases() -> pytest.MarkDecorator:
    cites = [
        pytest.param('src/queue.py:3', id='path'),
        pytest.param('git log -S sleep', id='command'),
        pytest.param('javascript:alert(1)', id='javascript-scheme'),
    ]
    return pytest.mark.parametrize('cite', cites)


def copied_cite_cases() -> pytest.MarkDecorator:
    cites = [pytest.param(PLAIN_URL, id='url-cite'), pytest.param('src/queue.py:3', id='path-cite')]
    return pytest.mark.parametrize('cite', cites)


class TestCites:
    def test_a_url_cite_becomes_a_link_that_shows_the_url(self) -> None:
        page = render_page(create_document(create_cited_node('claim', 'e1', PLAIN_URL)))

        (link,) = find_tags(page, 'a')
        assert link['href'] == PLAIN_URL
        assert f'>{PLAIN_URL}</a>' in page

    def test_a_link_does_not_leak_the_referrer(self) -> None:
        page = render_page(create_document(create_cited_node('claim', 'e1', PLAIN_URL)))

        (link,) = find_tags(page, 'a')
        assert 'noreferrer' in link['rel']

    @non_url_cite_cases()
    def test_a_cite_that_is_not_a_url_sits_in_code_with_no_link(self, cite: str) -> None:
        page = render_page(create_document(create_cited_node('claim', 'e1', cite)))

        assert cite in list_code_spans(page)
        assert find_tags(page, 'a') == []
        assert 'href' not in list_attribute_names(page)

    def test_the_http_scheme_is_a_link_too(self) -> None:
        page = render_page(
            create_document(create_cited_node('claim', 'e1', 'http://example.invalid/a'))
        )

        assert [link['href'] for link in find_tags(page, 'a')] == ['http://example.invalid/a']

    @copied_cite_cases()
    def test_a_cite_is_followed_by_a_copy_button_holding_the_cite(self, cite: str) -> None:
        page = render_page(create_document(create_cited_node('claim', 'e1', cite)))

        (block,) = list_cite_blocks(page)
        (button,) = find_buttons(page, 'copy')
        assert button['data-copy'] == cite
        assert button['type'] == 'button'
        assert block.endswith('>Copy</button>')

    def test_an_entry_with_no_cite_has_no_cite_block_and_no_copy_button(self) -> None:
        page = render_page(create_document(create_entry_node('claim', 'e1')))

        assert list_cite_blocks(page) == []
        assert find_buttons(page, 'copy') == []

    def test_each_cited_entry_gets_its_own_copy_button_in_order(self) -> None:
        document = create_document(
            create_cited_node('a', 'e1', 'src/a.py:1'),
            create_entry_node('b', 'e2'),
            create_cited_node('c', 'e3', PLAIN_URL),
        )

        page = render_page(document)

        assert [b['data-copy'] for b in find_buttons(page, 'copy')] == ['src/a.py:1', PLAIN_URL]
        assert list_copy_values(page).count(PLAIN_URL) == 1


class TestBackticks:
    def test_a_backtick_span_becomes_code_and_loses_its_ticks(self) -> None:
        page = render_page(create_point_document('call `time.sleep` before `retry`'))

        assert list_code_spans(page) == ['time.sleep', 'retry']
        assert '`' not in page

    def test_markup_inside_a_backtick_span_is_text_inside_the_code(self) -> None:
        page = render_page(create_point_document('try `<b>x</b>` now'))

        assert list_code_spans(page) == ['<b>x</b>']
        assert 'b' not in list_tag_names(page)

    def test_an_unpaired_backtick_stays_as_it_was_written(self) -> None:
        page = render_page(create_point_document('a ` b'))

        assert list_code_spans(page) == []
        assert 'a ` b' in page

    def test_prose_and_summary_lines_get_code_spans_too(self) -> None:
        document = create_document(prose=('see `prose.py`',)).replace_with(
            title='t',
            summary=(parse_line('at `HEAD`'),),
        )

        assert list_code_spans(render_page(document)) == ['HEAD', 'prose.py']
