"""HtmlPage: escaping in every place a value lands, links, copy buttons, code and content."""

from html import escape
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.documents import Citation
from red_thread_casefile.packaged import load_wording
from red_thread_core.documents import Document, Paragraph, Section, parse_line

from tests.casefile.pages.builders import (
    DOCUMENT_FIELDS,
    PAYLOADS,
    PLAIN_URL,
    create_document,
    create_document_carrying,
    payload_params,
)
from tests.casefile.pages.html_reading import (
    find_buttons,
    find_entries,
    find_tags,
    list_chip_groups,
    list_flags,
    list_item_refs,
    list_mermaid,
    list_tag_names,
    list_tags,
)
from tests.casefile.pages.promises import assert_page_holds_only_its_own_markup
from tests.casefile.writers.builders import create_entry_node
from tests.casefile.writers.reading import render_page

if TYPE_CHECKING:
    from tests.casefile.pages.builders import DocumentField


def create_url_cite(tail: str) -> str:
    return f'{PLAIN_URL}/{tail}'


def create_cited_document(cite: str) -> Document:
    entry = create_entry_node('claim').replace_with(citation=Citation(target=cite))
    return create_document(entry)


def create_prose_section(title: str, text: str) -> Section:
    return Section(title=title, blocks=(Paragraph(line=parse_line(text)),))


def document_field_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        'field', [pytest.param(name, id=name) for name in DOCUMENT_FIELDS]
    )


def payload_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('payload', payload_params())


class TestEscaping:
    @document_field_cases()
    @payload_cases()
    def test_markup_in_any_field_is_shown_as_text_and_never_as_an_element(
        self, field: DocumentField, payload: str
    ) -> None:
        page = render_page(create_document_carrying(field, payload))

        assert_page_holds_only_its_own_markup(page)
        assert page.lower().count('<script') == 3
        assert escape(payload) in page

    @document_field_cases()
    def test_an_ampersand_is_written_as_an_entity(self, field: DocumentField) -> None:
        page = render_page(create_document_carrying(field, 'fish & chips'))

        assert 'fish &amp; chips' in page
        assert 'fish & chips' not in page

    @payload_cases()
    def test_a_ref_lands_in_the_copy_attribute_and_the_button_text_as_text(
        self, payload: str
    ) -> None:
        page = render_page(create_document_carrying('item-ref', payload))

        (button, _) = find_buttons(page, 'ref')
        assert button['data-copy'] == payload
        assert list_item_refs(page)[0] == payload

    @payload_cases()
    def test_a_cite_lands_in_its_copy_attribute_as_text(self, payload: str) -> None:
        page = render_page(create_document_carrying('item-cite', payload))

        (button,) = find_buttons(page, 'copy')
        assert button['data-copy'] == payload

    @payload_cases()
    def test_a_thread_lands_in_the_entry_mark_and_the_chip_as_text(self, payload: str) -> None:
        page = render_page(create_document_carrying('item-thread', payload))

        (marked, _) = find_entries(page)
        assert marked['data-thread'] == payload
        groups = {group[0].group: group for group in list_chip_groups(page)}
        assert [(chip.value, chip.label) for chip in groups['thread']] == [
            ('', 'main ledger'),
            (payload, payload),
        ]

    @payload_cases()
    def test_a_kind_lands_in_the_entry_mark_as_text(self, payload: str) -> None:
        page = render_page(create_document_carrying('item-kind', payload))

        (marked, _) = find_entries(page)
        assert marked['data-kind'] == payload

    @payload_cases()
    def test_a_diagram_lands_in_its_pre_element_as_text(self, payload: str) -> None:
        page = render_page(create_document_carrying('item-diagram', payload))

        assert list_mermaid(page) == [payload]
        assert find_tags(page, 'pre') == [{'class': 'mermaid'}]

    @payload_cases()
    def test_a_map_line_lands_in_the_map_pre_element_as_text(self, payload: str) -> None:
        page = render_page(create_document_carrying('map-line', payload))

        (source,) = list_mermaid(page)
        assert source.splitlines()[-1] == payload
        assert find_tags(page, 'pre') == [{'class': 'mermaid'}]

    def test_a_quote_in_a_url_cite_cannot_break_out_of_the_href(self) -> None:
        cite = f'{PLAIN_URL}/x" onmouseover="alert(1)" data-x="'

        page = render_page(create_cited_document(cite))

        (link,) = find_tags(page, 'a')
        assert link['href'] == cite
        assert set(link) == {'href', 'rel'}

    def test_a_single_quote_and_angle_bracket_in_a_url_cite_stay_inside_the_href(self) -> None:
        cite = f"{PLAIN_URL}/it's<b>"

        page = render_page(create_cited_document(cite))

        (link,) = find_tags(page, 'a')
        assert link['href'] == cite
        assert 'b' not in list_tag_names(page)


class TestPropertyPageShape:
    texts = st.one_of(st.text(), st.sampled_from(PAYLOADS), st.text(alphabet='<>"\'&`/script '))
    fields = st.sampled_from(DOCUMENT_FIELDS)

    @given(field=fields, text=texts)
    def test_no_text_in_any_field_adds_an_element_an_attribute_or_a_script(
        self, field: DocumentField, text: str
    ) -> None:
        page = render_page(create_document_carrying(field, text))

        assert_page_holds_only_its_own_markup(page)
        assert page.lower().count('<script') == 3

    @given(cite=st.text().map(create_url_cite))
    def test_a_url_cite_of_any_text_stays_one_link_whose_href_is_the_cite(self, cite: str) -> None:
        page = render_page(create_cited_document(cite))

        (link,) = find_tags(page, 'a')
        assert link['href'] == cite
        assert set(link) == {'href', 'rel'}


class TestContent:
    def test_title_is_the_page_title_and_the_heading(self) -> None:
        page = render_page(create_document(title='Why jobs wait'))

        assert page.count('Why jobs wait') == 2

    def test_each_item_shows_its_ref_and_its_text(self) -> None:
        document = create_document(
            create_entry_node('first claim', 'e1'), create_entry_node('second claim', 'T1.e2')
        )

        page = render_page(document)

        assert list_item_refs(page) == ['e1', 'T1.e2']
        assert 'first claim' in page
        assert 'second claim' in page

    def test_flags_and_notes_are_shown_as_text(self) -> None:
        entry = create_entry_node().replace_with(
            notes=(load_wording().write_note('rests_on', 'a page'),),
            lead='1111111',
        )

        page = render_page(create_document(entry))

        assert list_flags(page) == ['lead, recorded at 1111111']
        assert 'rests on: a page' in page

    def test_an_item_with_no_flag_and_no_note_has_no_flag_element(self) -> None:
        page = render_page(create_document(create_entry_node()))

        assert list_flags(page) == []

    def test_sections_keep_their_document_order(self) -> None:
        document = Document(
            title='t',
            sections=(
                create_prose_section('Second thing', 'b'),
                create_prose_section('First thing', 'a'),
            ),
        )

        page = render_page(document)

        assert page.index('Second thing') < page.index('First thing')

    def test_the_page_names_every_element_it_used(self) -> None:
        page = render_page(create_cited_document(PLAIN_URL))

        used = {name for name, _ in list_tags(page)}
        assert used >= {'html', 'body', 'h1', 'h2', 'li', 'a', 'details', 'summary', 'button'}
