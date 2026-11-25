"""HtmlWriter over the tree: what an entry, a block and a section look like on the page."""

from dataclasses import replace
from html import escape

import pytest
from red_thread_casefile.documents import (
    Citation,
    Document,
    EntryList,
    Fact,
    Flowchart,
    Note,
    Paragraph,
    PointList,
    Section,
    parse_line,
    parse_value,
)
from red_thread_casefile.policy import Finding

from tests.casefile.pages.builders import PAYLOADS, payload_params
from tests.casefile.pages.html_reading import (
    find_entries,
    list_cited_quotes,
    list_claim_markup,
    list_facts,
    list_item_refs,
    list_mermaid,
    list_note_rows,
    list_sections,
    list_spans,
)
from tests.casefile.writers.builders import create_document, create_entry_node
from tests.casefile.writers.reading import render_page

PATH = 'src/queue.py:3'
URL = 'https://example.invalid/docs'


def payload_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('payload', payload_params())


class TestEntry:
    def test_an_entry_carries_its_ref_kind_and_thread(self) -> None:
        entry = replace(create_entry_node('claim', 'T1.e2'), kind='open', thread='T1')

        page = render_page(create_document(entry))

        assert list_item_refs(page) == ['T1.e2']
        assert find_entries(page) == [{'class': 'entry', 'data-kind': 'open', 'data-thread': 'T1'}]

    def test_code_spans_in_the_claim_are_code_elements(self) -> None:
        page = render_page(create_document(create_entry_node('run `make` first')))

        assert list_claim_markup(page) == ['run <code>make</code> first']

    def test_a_verdict_is_a_badge_before_the_claim(self) -> None:
        entry = replace(create_entry_node('maybe so'), verdict='INFERRED')

        page = render_page(create_document(entry))

        assert list_claim_markup(page) == [
            '<span class="verdict" data-verdict="INFERRED">INFERRED</span> maybe so'
        ]

    def test_a_path_citation_shows_its_quote_and_its_state(self) -> None:
        finding = Finding(ref='e1', cite=PATH, state='moved', moved_to=9)
        citation = Citation(target=PATH, quote='sleep(5)', finding=finding)

        page = render_page(create_document(replace(create_entry_node(), citation=citation)))

        (state,) = list_spans(page, 'state')
        assert state.body == 'moved to line 9'
        assert list_cited_quotes(page) == ['sleep(5)']

    def test_a_url_citation_is_a_link(self) -> None:
        entry = replace(create_entry_node(), citation=Citation(target=URL))

        page = render_page(create_document(entry))

        assert f'<a href="{URL}" rel="noreferrer">{URL}</a>' in page

    def test_notes_are_stamps_then_flags_then_notes(self) -> None:
        notes = (Note(kind='retired_by', value='e4'), Note(kind='source', value='scout'))
        entry = replace(create_entry_node(), lead='1111111', notes=notes)

        page = render_page(create_document(entry))

        assert list_note_rows(page) == [
            [
                ('stamp', 'round 1'),
                ('stamp', '2026-11-21'),
                ('flag', 'lead, recorded at 1111111'),
                ('', 'retired by e4'),
                ('', 'scout'),
            ]
        ]

    def test_a_diagram_is_drawn_under_the_claim(self) -> None:
        entry = replace(create_entry_node(), diagram='flowchart TD\n  A --> B')

        assert list_mermaid(render_page(create_document(entry))) == ['flowchart TD\n  A --> B']


class TestBlocks:
    def test_points_are_a_plain_list_without_refs(self) -> None:
        points = PointList(points=(parse_line('see `x`'),))
        document = Document(title='t', sections=(Section(title='Pointers', blocks=(points,)),))

        page = render_page(document)

        assert (
            '<ol class="plain"><li class="entry"><div><p class="claim">see <code>x</code>' in page
        )
        assert list_item_refs(page) == []

    def test_a_paragraph_is_a_p_element_with_code_spans(self) -> None:
        page = render_page(create_document(prose=('run `make`',)))

        assert '<p>run <code>make</code></p>' in page

    def test_a_flowchart_is_its_lines_in_one_mermaid_block(self) -> None:
        chart = Flowchart(lines=('flowchart LR', '  n0 --- n1'))
        document = Document(title='t', sections=(Section(title='Map', blocks=(chart,)),))

        assert list_mermaid(render_page(document)) == ['flowchart LR\n  n0 --- n1']


class TestSections:
    def test_a_section_of_entries_counts_them_and_names_its_kind(self) -> None:
        entries = EntryList(entries=(create_entry_node(), create_entry_node('b', 'e2')))
        section = Section(title='Known', blocks=(entries,), kind='known', note='Checked claims.')

        (reading,) = list_sections(render_page(Document(title='t', sections=(section,))))

        assert (reading.title, reading.count, reading.note) == ('Known', 2, 'Checked claims.')
        assert reading.attributes == {'class': 'section', 'data-kind': 'known', 'open': ''}

    def test_a_folded_section_without_entries_has_no_count_and_is_closed(self) -> None:
        section = Section(title='Goal', blocks=(Paragraph(line=parse_line('a')),), folded=True)

        (reading,) = list_sections(render_page(Document(title='t', sections=(section,))))

        assert (reading.count, reading.attributes) == (None, {'class': 'section'})


class TestFacts:
    def test_a_url_fact_is_a_link_and_other_facts_are_text(self) -> None:
        facts = (
            Fact(label='Page', value=parse_value(URL), wide=True),
            Fact(label='Kind', value=parse_value('bug')),
        )

        readings = list_facts(render_page(Document(title='t', facts=facts)))

        assert [(fact.label, fact.value, fact.wide, fact.link) for fact in readings] == [
            ('Page', URL, True, URL),
            ('Kind', 'bug', False, None),
        ]


class TestEscaping:
    def create_document_carrying(self, text: str) -> Document:
        citation = Citation(target=text, quote=text)
        entry = replace(
            create_entry_node(text),
            citation=citation,
            notes=(Note(kind='source', value=text),),
            diagram=text,
            thread=text,
        )
        section = Section(title=text, note=text, blocks=(EntryList(entries=(entry,)),))
        chart = Section(title='Map', blocks=(Flowchart(lines=(text,)),))
        facts = (Fact(label=text, value=parse_value(text)),)
        summary = (parse_line(text),)
        return Document(title=text, summary=summary, facts=facts, sections=(section, chart))

    @payload_cases()
    def test_no_payload_reaches_the_page_unescaped(self, payload: str) -> None:
        page = render_page(self.create_document_carrying(payload))

        assert payload not in page
        assert escape(payload) in page

    def test_the_payloads_cover_a_closing_pre(self) -> None:
        assert any('</pre>' in payload for payload in PAYLOADS)
