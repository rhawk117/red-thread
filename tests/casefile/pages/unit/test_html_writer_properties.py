"""HtmlPage: the text of every field comes back from the page, and only page markup appears."""

import re
from html import unescape
from typing import TYPE_CHECKING, get_args

from hypothesis import example, given
from hypothesis import strategies as st
from red_thread_casefile.documents import (
    CitationNode,
    FindingList,
    FindingNode,
    Note,
    NoteKind,
    list_document_findings,
)
from red_thread_casefile.domain import FINDING_KINDS
from red_thread_casefile.packaged import load_wording, read_asset
from red_thread_core.documents import Document, Flowchart, Paragraph, PointList, Section, parse_line

from tests.casefile.documents.reading import join_line
from tests.casefile.findings.strategies import optional
from tests.casefile.pages.html_reading import (
    find_buttons,
    find_finding_items,
    find_tags,
    list_code_spans,
    list_copy_values,
    list_mermaid,
    list_scripts,
    list_styles,
)
from tests.casefile.pages.promises import assert_page_holds_only_its_own_markup
from tests.casefile.pages.strategies import many, texts
from tests.casefile.writers.builders import create_finding_node
from tests.casefile.writers.reading import render_page
from tests.core.timekeeping.clock import DAY

if TYPE_CHECKING:
    from collections.abc import Sequence

    from red_thread_core.documents import Block, Line

ANY_TAG = re.compile(r'<[^>]*>')
TITLE = re.compile(r'<title>(.*?)</title>', re.DOTALL)
HEADING = re.compile(r'<h1[^>]*>(.*?)</h1>', re.DOTALL)
META = re.compile(r'<ul class="meta">(.*?)</ul>', re.DOTALL)
LIST_ITEM = re.compile(r'<li>(.*?)</li>', re.DOTALL)
SECTION_TITLE = re.compile(r'<h2>(.*?)</h2>', re.DOTALL)
PROSE = re.compile(r'<p>(.*?)</p>', re.DOTALL)
CLAIM = re.compile(r'<p class="claim">(.*?)</p>', re.DOTALL)
FINDING_ID = re.compile(r'<button type="button" class="finding-id"[^>]*>(.*?)</button>', re.DOTALL)
PATH_CITE = re.compile(r'<p class="citation"><code>(.*?)</code>', re.DOTALL)
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


def create_page_of(*blocks: Block) -> str:
    document = Document(title='t', sections=(Section(title='s', blocks=blocks),))
    return render_page(document)


def render_claim(text: str) -> str:
    return create_page_of(PointList(points=(parse_line(text),)))


def create_map(lines: list[str]) -> Section:
    chart = Flowchart(lines=(read_asset('map.mmd').rstrip(), *lines))
    return Section(title='Map', blocks=(chart,), note=load_wording().map_note)


def list_map_lines(document: Document) -> list[str]:
    blocks = (block for section in document.appendix for block in section.blocks)
    charts = (block for block in blocks if isinstance(block, Flowchart))
    return [line for chart in charts for line in chart.lines[1:]]


def list_blocks(document: Document) -> list[Block]:
    return [block for section in document.sections for block in section.blocks]


def list_block_claims(block: Block) -> tuple[Line, ...]:
    if isinstance(block, FindingList):
        return tuple(finding.claim for finding in block.findings)

    if isinstance(block, PointList):
        return block.points

    return ()


def list_claims(document: Document) -> list[str]:
    blocks = list_blocks(document)
    return [join_line(claim) for block in blocks for claim in list_block_claims(block)]


def list_prose(document: Document) -> list[str]:
    blocks = list_blocks(document)
    return [join_line(block.line) for block in blocks if isinstance(block, Paragraph)]


def list_path_citations(findings: Sequence[FindingNode]) -> list[str]:
    return [
        finding.citation_node.target for finding in findings if finding.citation_node is not None
    ]


def list_lead_flags(findings: Sequence[FindingNode]) -> list[str]:
    return [f'lead, recorded at {finding.lead}' for finding in findings if finding.lead is not None]


class TestHtmlPageProperties:
    lines = st.builds(parse_line, texts)
    notes = st.builds(Note, kind=st.sampled_from(get_args(NoteKind.__value__)), text=texts)
    findings = st.builds(
        FindingNode,
        finding_id=texts,
        kind=st.sampled_from(FINDING_KINDS),
        claim=lines,
        round=st.integers(min_value=1, max_value=9),
        at=st.just(DAY),
        thread=optional(texts),
        citation_node=optional(st.builds(CitationNode, target=texts.filter(is_not_url))),
        notes=many(notes, 2),
        lead=optional(texts),
        diagram=optional(texts),
    )
    blocks = st.one_of(
        st.builds(Paragraph, line=lines),
        st.builds(FindingList, findings=many(findings, 3)),
        st.builds(PointList, points=many(lines, 3)),
    )
    sections = st.builds(Section, title=texts, blocks=many(blocks, 3))
    maps = st.builds(create_map, st.lists(texts.filter(is_one_line), min_size=1, max_size=3))
    documents = st.builds(
        Document,
        title=texts,
        summary=many(lines, 3),
        sections=many(sections, 3),
        appendix=many(maps, 1),
    )
    urls = st.builds('https://{}'.format, texts)

    @given(document=documents)
    @example(document=Document(title='<b>&"\'', summary=(parse_line('a & b'),), sections=()))
    def test_the_text_of_every_field_is_what_the_page_reads_back(self, document: Document) -> None:
        page = render_page(document)

        findings = list_document_findings(document)
        meta = ''.join(META.findall(page))
        assert read_texts(page, TITLE) == [document.title]
        assert read_texts(page, HEADING) == [document.title]
        assert read_texts(meta, LIST_ITEM) == list(map(join_line, document.summary))
        titles = [section.title for section in document.sections]
        assert read_texts(page, SECTION_TITLE) == [*titles, *(['Map'] * bool(document.appendix))]
        assert read_texts(page, PROSE) == list_prose(document)
        assert read_texts(page, CLAIM) == list_claims(document)
        assert read_texts(page, FINDING_ID) == [finding.finding_id for finding in findings]
        assert read_texts(page, PATH_CITE) == list_path_citations(findings)
        assert read_texts(page, FLAG) == list_lead_flags(findings)
        assert list_notes(page) == [note.text for finding in findings for note in finding.notes]

    @given(document=documents)
    def test_every_value_that_lands_in_an_attribute_is_the_value_the_finding_held(
        self, document: Document
    ) -> None:
        page = render_page(document)

        findings = list_document_findings(document)
        assert [
            finding.get('data-kind')
            for finding in find_finding_items(page)
            if 'data-kind' in finding
        ] == [finding.kind for finding in findings]
        assert [
            finding.get('data-thread')
            for finding in find_finding_items(page)
            if 'data-thread' in finding
        ] == [finding.thread or '' for finding in findings]
        assert [button['data-copy'] for button in find_buttons(page, 'finding-id')] == [
            finding.finding_id for finding in findings
        ]
        assert [
            button['data-copy'] for button in find_buttons(page, 'copy')
        ] == list_path_citations(findings)
        assert len(find_finding_items(page)) == len(list_claims(document))

    @given(document=documents)
    def test_every_finding_diagram_and_the_map_come_back_as_mermaid_source(
        self, document: Document
    ) -> None:
        page = render_page(document)

        diagrams = [
            finding.diagram
            for finding in list_document_findings(document)
            if finding.diagram is not None
        ]
        drawn = list_mermaid(page)
        assert drawn[: len(diagrams)] == diagrams
        assert len(drawn) == len(diagrams) + bool(document.appendix)
        expected = [*read_asset('map.mmd').splitlines(), *list_map_lines(document)]
        assert not document.appendix or drawn[-1].splitlines() == expected

    @given(document=documents)
    def test_no_tag_appears_that_the_writer_does_not_emit(self, document: Document) -> None:
        page = render_page(document)

        assert_page_holds_only_its_own_markup(page)

    @given(first=documents, second=documents)
    def test_the_script_and_the_styles_hold_nothing_from_the_document(
        self, first: Document, second: Document
    ) -> None:
        pages = [render_page(document) for document in (first, second)]

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
    def test_a_url_citation_is_one_link_to_that_url_and_shows_it(self, url: str) -> None:
        finding = create_finding_node('claim').replace_with(citation_node=CitationNode(target=url))

        page = create_page_of(FindingList(findings=(finding,)))

        assert find_tags(page, 'a') == [{'href': url, 'rel': 'noreferrer'}]
        assert read_texts(page, ANCHOR) == [url]
        assert list_code_spans(page) == []
        assert list_copy_values(page) == [finding.finding_id, url]
        assert [button['data-copy'] for button in find_buttons(page, 'copy')] == [url]

    @given(text=st.text(alphabet='$${}abtitlesumry '))
    def test_a_dollar_name_in_a_field_is_shown_as_written_and_never_filled_in(
        self, text: str
    ) -> None:
        page = render_claim(text)

        assert read_texts(page, CLAIM) == [text]
        assert read_texts(page, TITLE) == ['t']
        assert read_texts(page, HEADING) == ['t']
