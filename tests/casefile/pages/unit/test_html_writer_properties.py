"""HtmlWriter: the text of every field comes back from the page, and only page markup appears."""

import re
from html import unescape

from hypothesis import example, given
from hypothesis import strategies as st
from red_thread_casefile.assets import read_asset
from red_thread_casefile.domain import ENTRY_KINDS
from red_thread_casefile.pages import HtmlWriter
from red_thread_casefile.views import Document, Item, Section

from tests.casefile.entries.strategies import optional
from tests.casefile.pages.html_reading import (
    find_buttons,
    find_entries,
    find_tags,
    list_code_spans,
    list_copy_values,
    list_mermaid,
    list_scripts,
    list_styles,
)
from tests.casefile.pages.promises import assert_page_holds_only_its_own_markup

ANY_TAG = re.compile(r'<[^>]*>')
TITLE = re.compile(r'<title>(.*?)</title>', re.DOTALL)
HEADING = re.compile(r'<h1[^>]*>(.*?)</h1>', re.DOTALL)
META = re.compile(r'<ul class="meta">(.*?)</ul>', re.DOTALL)
LIST_ITEM = re.compile(r'<li>(.*?)</li>', re.DOTALL)
SECTION_TITLE = re.compile(r'<h2>(.*?)</h2>', re.DOTALL)
PROSE = re.compile(r'<p>(.*?)</p>', re.DOTALL)
CLAIM = re.compile(r'<p class="claim">(.*?)</p>', re.DOTALL)
REF = re.compile(r'<button type="button" class="ref"[^>]*>(.*?)</button>', re.DOTALL)
PATH_CITE = re.compile(r'<p class="cite"><code>(.*?)</code>', re.DOTALL)
FLAG = re.compile(r'<li class="flag">(.*?)</li>', re.DOTALL)
NOTE_LIST = re.compile(r'<ul class="notes">(.*?)</ul>', re.DOTALL)
ANCHOR = re.compile(r'<a [^>]*>(.*?)</a>', re.DOTALL)


def read_texts(page: str, pattern: re.Pattern[str]) -> list[str]:
    return [unescape(ANY_TAG.sub('', found)) for found in pattern.findall(page)]


def is_not_url(text: str) -> bool:
    return not text.startswith(('http://', 'https://'))


def is_one_line(text: str) -> bool:
    return text.splitlines() == [text]


def list_notes(page: str) -> list[str]:
    blocks = NOTE_LIST.findall(page)
    return [unescape(note) for block in blocks for note in LIST_ITEM.findall(block)]


def render_claim(text: str) -> str:
    item = Item(text=text)
    document = Document(title='t', sections=(Section(title='s', items=(item,)),))
    return HtmlWriter(document=document).render()


def list_items(document: Document) -> list[Item]:
    return [item for section in document.sections for item in section.items]


texts = st.text(
    alphabet=st.characters(blacklist_categories=('Cs',), blacklist_characters='`'), max_size=30
)


def many[Value](
    strategy: st.SearchStrategy[Value], size: int
) -> st.SearchStrategy[tuple[Value, ...]]:
    return st.builds(tuple, st.lists(strategy, max_size=size))


class TestHtmlWriterProperties:
    items = st.builds(
        Item,
        text=texts,
        ref=optional(texts),
        cite=optional(texts.filter(is_not_url)),
        notes=many(texts, 2),
        flags=many(texts, 2),
        kind=optional(st.sampled_from(ENTRY_KINDS)),
        thread=optional(texts),
        diagram=optional(texts),
    )
    sections = st.builds(Section, title=texts, items=many(items, 3), prose=many(texts, 2))
    documents = st.builds(
        Document,
        title=texts,
        summary=many(texts, 3),
        sections=many(sections, 3),
        map_lines=many(texts.filter(is_one_line), 3),
    )
    urls = st.builds('https://{}'.format, texts)

    @given(document=documents)
    @example(document=Document(title='<b>&"\'', summary=('a & b',), sections=()))
    def test_the_text_of_every_field_is_what_the_page_reads_back(self, document: Document) -> None:
        page = HtmlWriter(document=document).render()

        items = list_items(document)
        meta = ''.join(META.findall(page))
        assert read_texts(page, TITLE) == [document.title]
        assert read_texts(page, HEADING) == [document.title]
        assert read_texts(meta, LIST_ITEM) == list(document.summary)
        titles = [section.title for section in document.sections]
        assert read_texts(page, SECTION_TITLE) == [*titles, *(['Map'] * bool(document.map_lines))]
        assert read_texts(page, PROSE) == [line for s in document.sections for line in s.prose]
        assert read_texts(page, CLAIM) == [item.text for item in items]
        assert read_texts(page, REF) == [item.ref for item in items if item.ref is not None]
        assert read_texts(page, PATH_CITE) == [item.cite for item in items if item.cite is not None]
        assert read_texts(page, FLAG) == [flag for item in items for flag in item.flags]
        assert list_notes(page) == [note for item in items for note in item.notes]

    @given(document=documents)
    def test_every_value_that_lands_in_an_attribute_is_the_value_the_item_held(
        self, document: Document
    ) -> None:
        page = HtmlWriter(document=document).render()

        items = list_items(document)
        refs = [item for item in items if item.ref is not None]
        assert [entry.get('data-kind') for entry in find_entries(page) if 'data-kind' in entry] == [
            item.kind or '' for item in refs
        ]
        assert [
            entry.get('data-thread') for entry in find_entries(page) if 'data-thread' in entry
        ] == [item.thread or '' for item in refs]
        assert [button['data-copy'] for button in find_buttons(page, 'ref')] == [
            item.ref for item in refs
        ]
        assert [button['data-copy'] for button in find_buttons(page, 'copy')] == [
            item.cite for item in items if item.cite is not None
        ]
        assert len(find_entries(page)) == len(items)

    @given(document=documents)
    def test_every_item_diagram_and_the_map_come_back_as_mermaid_source(
        self, document: Document
    ) -> None:
        page = HtmlWriter(document=document).render()

        diagrams = [item.diagram for item in list_items(document) if item.diagram is not None]
        drawn = list_mermaid(page)
        assert drawn[: len(diagrams)] == diagrams
        assert len(drawn) == len(diagrams) + bool(document.map_lines)
        expected = [*read_asset('map.mmd').splitlines(), *document.map_lines]
        assert not document.map_lines or drawn[-1].splitlines() == expected

    @given(document=documents)
    def test_no_tag_appears_that_the_writer_does_not_emit(self, document: Document) -> None:
        page = HtmlWriter(document=document).render()

        assert_page_holds_only_its_own_markup(page)

    @given(first=documents, second=documents)
    def test_the_script_and_the_styles_hold_nothing_from_the_document(
        self, first: Document, second: Document
    ) -> None:
        pages = [HtmlWriter(document=document).render() for document in (first, second)]

        inline = [next(s.body for s in list_scripts(p) if 'src' not in s.attributes) for p in pages]
        styles = [sorted(style.body for style in list_styles(page)) for page in pages]
        assert inline[0] == inline[1]
        assert styles[0] == styles[1]

    @given(before=texts, code=texts.filter(bool), after=texts)
    def test_a_code_span_in_a_claim_is_one_code_element_and_its_text_stays(
        self, before: str, code: str, after: str
    ) -> None:
        page = render_claim(f'{before}`{code}`{after}')

        assert list_code_spans(page) == [code]
        assert read_texts(page, CLAIM) == [f'{before}{code}{after}']

    @given(before=texts, after=texts)
    def test_a_lone_backtick_in_a_claim_stays_in_the_text(self, before: str, after: str) -> None:
        text = f'{before}`{after}'

        page = render_claim(text)

        assert list_code_spans(page) == []
        assert read_texts(page, CLAIM) == [text]

    @given(url=urls)
    def test_a_url_cite_is_one_link_to_that_url_and_shows_it(self, url: str) -> None:
        item = Item(text='claim', cite=url)
        document = Document(title='t', sections=(Section(title='s', items=(item,)),))

        page = HtmlWriter(document=document).render()

        assert find_tags(page, 'a') == [{'href': url, 'rel': 'noreferrer'}]
        assert read_texts(page, ANCHOR) == [url]
        assert list_code_spans(page) == []
        assert list_copy_values(page) == [url]

    @given(text=st.text(alphabet='$${}abtitlesumry '))
    def test_a_dollar_name_in_a_field_is_shown_as_written_and_never_filled_in(
        self, text: str
    ) -> None:
        page = render_claim(text)

        assert read_texts(page, CLAIM) == [text]
        assert read_texts(page, TITLE) == ['t']
        assert read_texts(page, HEADING) == ['t']
