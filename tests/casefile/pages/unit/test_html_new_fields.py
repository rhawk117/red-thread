"""HtmlWriter: where verdict, state, stamps, quote, section data and facts land, for any text."""

from datetime import datetime
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.domain import ENTRY_KINDS, VERDICTS
from red_thread_casefile.pages import HtmlWriter
from red_thread_casefile.policy import CITE_STATES, Finding
from red_thread_casefile.views import Document, Fact, Item, Section

from tests.casefile.entries.strategies import optional
from tests.casefile.pages.builders import create_document_carrying, payload_params
from tests.casefile.pages.html_reading import (
    find_tags,
    list_cited_quotes,
    list_facts,
    list_item_refs,
    list_note_rows,
    list_sections,
    list_spans,
)
from tests.casefile.pages.strategies import many, texts

if TYPE_CHECKING:
    from tests.casefile.pages.builders import DocumentField

URL_PREFIX = ('http://', 'https://')
CITED_PATH = 'src/queue.py:3'
DAY_WIDTH = 10


def render(document: Document) -> str:
    return HtmlWriter(document=document).render()


def is_not_url(text: str) -> bool:
    return not text.startswith(URL_PREFIX)


def label_state(finding: Finding) -> str:
    if finding.state == 'moved' and finding.moved_to is not None:
        return f'moved to line {finding.moved_to}'
    return finding.state


def list_all_items(document: Document) -> list[Item]:
    shown = [item for section in document.sections for item in section.items]
    return [*shown, *document.retired]


def payload_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('payload', payload_params())


class TestNewFieldsLandAsText:
    def read(self, field: DocumentField, payload: str) -> str:
        return render(create_document_carrying(field, payload))

    @payload_cases()
    def test_a_verdict_is_the_badge_text_and_its_data_attribute(self, payload: str) -> None:
        (badge,) = list_spans(self.read('item-verdict', payload), 'verdict')

        assert (badge.body, badge.attributes['data-verdict']) == (payload, payload)

    @payload_cases()
    def test_a_citation_state_is_the_badge_text_and_its_data_attribute(self, payload: str) -> None:
        (badge,) = list_spans(self.read('item-state', payload), 'state')

        assert (badge.body, badge.attributes['data-state']) == (payload, payload)

    @payload_cases()
    def test_a_timestamp_is_the_datetime_attribute_and_its_day_is_the_text(
        self, payload: str
    ) -> None:
        page = self.read('item-at', payload)

        assert find_tags(page, 'time') == [{'datetime': payload}]
        assert ('stamp', payload[:DAY_WIDTH]) in list_note_rows(page)[0]

    @payload_cases()
    def test_a_quote_is_the_text_of_one_pre_element_after_the_cite(self, payload: str) -> None:
        page = self.read('item-quote', payload)

        assert list_cited_quotes(page) == [payload]
        assert find_tags(page, 'pre') == [{'class': 'quote'}]

    @payload_cases()
    def test_a_section_note_is_the_about_text_and_a_kind_the_data_attribute(
        self, payload: str
    ) -> None:
        note = list_sections(self.read('section-note', payload))[0]
        kind = list_sections(self.read('section-kind', payload))[0]

        assert note.note == payload
        assert kind.attributes['data-kind'] == payload

    @payload_cases()
    def test_a_fact_label_and_a_fact_value_are_text(self, payload: str) -> None:
        (labelled,) = list_facts(self.read('fact-label', payload))
        (valued,) = list_facts(self.read('fact-value', payload))

        assert (labelled.label, labelled.link) == (payload, None)
        assert (valued.value, valued.link) == (payload, None)

    @payload_cases()
    def test_a_url_fact_value_is_one_link_whose_href_is_the_value(self, payload: str) -> None:
        (fact,) = list_facts(self.read('fact-url-value', payload))

        assert fact.link == fact.value
        assert fact.value.endswith(payload)
        assert find_tags(self.read('fact-url-value', payload), 'a') == [
            {'href': fact.value, 'rel': 'noreferrer'}
        ]

    @payload_cases()
    def test_a_retired_entry_text_and_note_are_text_in_the_retired_fold(self, payload: str) -> None:
        text_page = self.read('retired-text', payload)
        note_page = self.read('retired-note', payload)

        assert list_item_refs(text_page)[-1] == 'e9'
        assert list_sections(text_page)[-1].title == 'Retired'
        assert ('', payload) in list_note_rows(note_page)[-1]


class TestNewFieldsRoundTrip:
    findings = st.builds(
        Finding,
        ref=st.just('e1'),
        cite=st.just(CITED_PATH),
        state=st.sampled_from(CITE_STATES),
        moved_to=optional(st.integers(min_value=1, max_value=999)),
    )
    items = st.builds(
        Item,
        text=texts,
        ref=st.just('e1'),
        cite=st.just(CITED_PATH),
        notes=many(texts, 2),
        kind=st.sampled_from(ENTRY_KINDS),
        verdict=optional(st.sampled_from(VERDICTS)),
        round=optional(st.integers(min_value=0, max_value=999)),
        at=optional(st.datetimes().map(datetime.isoformat)),
        quote=optional(texts),
        finding=optional(findings),
    )
    sections = st.builds(
        Section,
        title=texts,
        items=many(items, 3),
        kind=optional(st.sampled_from(ENTRY_KINDS)),
        note=texts,
    )
    facts = st.builds(Fact, label=texts, value=texts.filter(is_not_url), wide=st.booleans())
    documents = st.builds(
        Document,
        title=texts,
        sections=many(sections, 3),
        facts=many(facts, 4),
        retired=many(items, 3),
    )

    @given(document=documents)
    def test_facts_come_back_in_order_with_their_width_and_no_link(
        self, document: Document
    ) -> None:
        read = [
            (fact.label, fact.value, fact.wide, fact.link) for fact in list_facts(render(document))
        ]

        assert read == [(fact.label, fact.value, fact.wide, None) for fact in document.facts]

    @given(document=documents)
    def test_every_verdict_and_state_comes_back_in_page_order(self, document: Document) -> None:
        page = render(document)

        items = list_all_items(document)
        assert [span.body for span in list_spans(page, 'verdict')] == [
            item.verdict for item in items if item.verdict
        ]
        assert [span.body for span in list_spans(page, 'state')] == [
            label_state(item.finding) for item in items if item.finding
        ]

    @given(document=documents)
    def test_every_quote_round_and_timestamp_comes_back_in_page_order(
        self, document: Document
    ) -> None:
        page = render(document)

        items = list_all_items(document)
        stamps = [text for row in list_note_rows(page) for role, text in row if role == 'stamp']
        assert list_cited_quotes(page) == [item.quote for item in items if item.quote is not None]
        assert [stamp for stamp in stamps if stamp.startswith('round ')] == [
            f'round {item.round}' for item in items if item.round is not None
        ]
        assert [tag['datetime'] for tag in find_tags(page, 'time')] == [
            item.at for item in items if item.at is not None
        ]

    @given(document=documents)
    def test_every_section_title_and_note_comes_back_in_order(self, document: Document) -> None:
        shown = list_sections(render(document))[: len(document.sections)]

        assert [(section.title, section.note or '') for section in shown] == [
            (section.title, section.note) for section in document.sections
        ]
