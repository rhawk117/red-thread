"""HtmlWriter: links, copy buttons and code spans."""

import pytest
from red_thread_casefile.pages import HtmlWriter
from red_thread_casefile.views import Document, Item

from tests.casefile.pages.builders import (
    PLAIN_URL,
    create_document,
)
from tests.casefile.pages.html_reading import (
    find_buttons,
    find_tags,
    list_attribute_names,
    list_cite_blocks,
    list_code_spans,
    list_copy_values,
    list_tag_names,
)


def render(document: Document) -> str:
    return HtmlWriter(document=document).render()


class TestCites:
    def test_a_url_cite_becomes_a_link_that_shows_the_url(self) -> None:
        page = render(create_document(Item(text='claim', cite=PLAIN_URL, ref='e1')))

        (link,) = find_tags(page, 'a')
        assert link['href'] == PLAIN_URL
        assert f'>{PLAIN_URL}</a>' in page

    def test_a_link_does_not_leak_the_referrer(self) -> None:
        page = render(create_document(Item(text='claim', cite=PLAIN_URL)))

        (link,) = find_tags(page, 'a')
        assert 'noreferrer' in link['rel']

    @pytest.mark.parametrize('cite', ['src/queue.py:3', 'git log -S sleep', 'javascript:alert(1)'])
    def test_a_cite_that_is_not_a_url_sits_in_code_with_no_link(self, cite: str) -> None:
        page = render(create_document(Item(text='claim', cite=cite)))

        assert cite in list_code_spans(page)
        assert find_tags(page, 'a') == []
        assert 'href' not in list_attribute_names(page)

    def test_the_http_scheme_is_a_link_too(self) -> None:
        page = render(create_document(Item(text='claim', cite='http://example.invalid/a')))

        assert [link['href'] for link in find_tags(page, 'a')] == ['http://example.invalid/a']

    @pytest.mark.parametrize('cite', [PLAIN_URL, 'src/queue.py:3'], ids=['url-cite', 'path-cite'])
    def test_a_cite_is_followed_by_a_copy_button_holding_the_cite(self, cite: str) -> None:
        page = render(create_document(Item(text='claim', cite=cite, ref='e1')))

        (block,) = list_cite_blocks(page)
        (button,) = find_buttons(page, 'copy')
        assert button['data-copy'] == cite
        assert button['type'] == 'button'
        assert block.endswith('>Copy</button>')

    def test_an_item_with_no_cite_has_no_cite_block_and_no_copy_button(self) -> None:
        page = render(create_document(Item(text='claim', ref='e1')))

        assert list_cite_blocks(page) == []
        assert find_buttons(page, 'copy') == []

    def test_each_cited_item_gets_its_own_copy_button_in_order(self) -> None:
        document = create_document(
            Item(text='a', ref='e1', cite='src/a.py:1'),
            Item(text='b', ref='e2'),
            Item(text='c', ref='e3', cite=PLAIN_URL),
        )

        page = render(document)

        assert [b['data-copy'] for b in find_buttons(page, 'copy')] == ['src/a.py:1', PLAIN_URL]
        assert list_copy_values(page).count(PLAIN_URL) == 1


class TestBackticks:
    def test_a_backtick_span_becomes_code_and_loses_its_ticks(self) -> None:
        page = render(create_document(Item(text='call `time.sleep` before `retry`')))

        assert list_code_spans(page) == ['time.sleep', 'retry']
        assert '`' not in page

    def test_markup_inside_a_backtick_span_is_text_inside_the_code(self) -> None:
        page = render(create_document(Item(text='try `<b>x</b>` now')))

        assert list_code_spans(page) == ['<b>x</b>']
        assert 'b' not in list_tag_names(page)

    def test_an_unpaired_backtick_stays_as_it_was_written(self) -> None:
        page = render(create_document(Item(text='a ` b')))

        assert list_code_spans(page) == []
        assert 'a ` b' in page

    def test_prose_and_summary_lines_get_code_spans_too(self) -> None:
        document = create_document(prose=('see `prose.py`',))
        document = Document(title='t', summary=('at `HEAD`',), sections=document.sections)

        assert list_code_spans(render(document)) == ['HEAD', 'prose.py']
