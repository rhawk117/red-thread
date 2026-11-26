"""HtmlPage: where verdict, state, stamps, quote, section data and facts land, for any text."""

from datetime import datetime
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.boards import RETIRED_NOTE
from red_thread_casefile.documents import (
    Citation,
    EntryList,
    EntryNode,
    Note,
    list_document_entries,
    list_entries_block,
    list_section_entries,
)
from red_thread_casefile.domain import ENTRY_KINDS, VERDICTS
from red_thread_casefile.policy import CITE_STATES, Finding
from red_thread_core.documents import Document, Fact, Section, parse_line, parse_value

from tests.casefile.documents.builders import MOMENT
from tests.casefile.documents.reading import join_line
from tests.casefile.entries.strategies import optional
from tests.casefile.pages.builders import (
    CITED_PATH,
    STAMP_DAY,
    create_document_carrying,
    payload_params,
)
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
from tests.casefile.writers.reading import render_page

if TYPE_CHECKING:
    from tests.casefile.pages.builders import DocumentField

URL_PREFIX = ('http://', 'https://')


def is_not_url(text: str) -> bool:
    return not text.startswith(URL_PREFIX)


def label_state(finding: Finding) -> str:
    if finding.state == 'moved' and finding.moved_to is not None:
        return f'moved to line {finding.moved_to}'
    return finding.state


def create_retired(entries: tuple[EntryNode, ...]) -> tuple[Section, ...]:
    if not entries:
        return ()
    blocks = (EntryList(entries=entries),)
    return (Section(title='Retired', blocks=blocks, note=RETIRED_NOTE, folded=True),)


def list_all_entries(document: Document) -> list[EntryNode]:
    retired = [entry for section in document.appendix for entry in list_section_entries(section)]
    return [*list_document_entries(document), *retired]


def find_finding(entry: EntryNode) -> Finding | None:
    if entry.citation is None:
        return None
    return entry.citation.finding


def find_quote(entry: EntryNode) -> str | None:
    if entry.citation is None:
        return None
    return entry.citation.quote


def payload_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('payload', payload_params())


class TestNewFieldsLandAsText:
    def read(self, field: DocumentField, payload: str) -> str:
        return render_page(create_document_carrying(field, payload))

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

        assert find_tags(page, 'time') == [
            {'datetime': f'{STAMP_DAY}{payload}'},
            {'datetime': MOMENT},
        ]
        assert ('stamp', STAMP_DAY) in list_note_rows(page)[0]

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
    citations = st.builds(
        Citation, target=st.just(CITED_PATH), quote=optional(texts), finding=optional(findings)
    )
    entries = st.builds(
        EntryNode,
        ref=st.just('e1'),
        kind=st.sampled_from(ENTRY_KINDS),
        claim=st.builds(parse_line, texts),
        verdict=optional(st.sampled_from(VERDICTS)),
        round=st.integers(min_value=0, max_value=999),
        at=st.datetimes().map(datetime.isoformat),
        citation=citations,
        notes=many(st.builds(Note, kind=st.just('source'), value=texts), 2),
    )
    sections = st.builds(
        Section,
        title=texts,
        blocks=st.builds(list_entries_block, many(entries, 3)),
        kind=optional(st.sampled_from(ENTRY_KINDS)),
        note=texts,
    )
    facts = st.builds(
        Fact,
        label=texts,
        value=st.builds(parse_value, texts.filter(is_not_url)),
        wide=st.booleans(),
    )
    documents = st.builds(
        Document,
        title=texts,
        sections=many(sections, 3),
        facts=many(facts, 4),
        appendix=st.builds(create_retired, many(entries, 3)),
    )

    @given(document=documents)
    def test_facts_come_back_in_order_with_their_width_and_no_link(
        self, document: Document
    ) -> None:
        read = [
            (fact.label, fact.value, fact.wide, fact.link)
            for fact in list_facts(render_page(document))
        ]

        assert read == [
            (fact.label, join_line(fact.value), fact.wide, None) for fact in document.facts
        ]

    @given(document=documents)
    def test_every_verdict_and_state_comes_back_in_page_order(self, document: Document) -> None:
        page = render_page(document)

        entries = list_all_entries(document)
        assert [span.body for span in list_spans(page, 'verdict')] == [
            entry.verdict for entry in entries if entry.verdict
        ]
        assert [span.body for span in list_spans(page, 'state')] == [
            label_state(finding) for finding in map(find_finding, entries) if finding
        ]

    @given(document=documents)
    def test_every_quote_round_and_timestamp_comes_back_in_page_order(
        self, document: Document
    ) -> None:
        page = render_page(document)

        entries = list_all_entries(document)
        stamps = [text for row in list_note_rows(page) for role, text in row if role == 'stamp']
        quotes = [quote for quote in map(find_quote, entries) if quote is not None]
        assert list_cited_quotes(page) == quotes
        assert [stamp for stamp in stamps if stamp.startswith('round ')] == [
            f'round {entry.round}' for entry in entries
        ]
        assert [tag['datetime'] for tag in find_tags(page, 'time')] == [
            entry.at for entry in entries
        ]

    @given(document=documents)
    def test_every_section_title_and_note_comes_back_in_order(self, document: Document) -> None:
        shown = list_sections(render_page(document))[: len(document.sections)]

        assert [(section.title, section.note or '') for section in shown] == [
            (section.title, section.note) for section in document.sections
        ]
