"""MarkdownWriter: how a finding, its citation and its id are written, and the layout."""

from typing import TYPE_CHECKING

import pytest
from hypothesis import example, given
from red_thread_casefile.documents import CitationNode, list_section_findings
from red_thread_casefile.packaged import load_wording
from red_thread_casefile.policy import CitationCheck
from red_thread_core.documents import (
    Document,
    Flowchart,
    Paragraph,
    PointList,
    Section,
    Text,
    parse_line,
)

from tests.casefile.lenses.cases import citation_shape_params
from tests.casefile.writers.builders import create_document, create_finding_node
from tests.casefile.writers.reading import list_item_lines, render_markdown
from tests.casefile.writers.strategies import documents

if TYPE_CHECKING:
    from tests.casefile.lenses.cases import CitationShape


def citation_shape_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('shape', citation_shape_params())


class TestFindingLine:
    @citation_shape_cases()
    def test_finding_is_text_then_citation_then_finding_id_at_the_end_of_the_line(
        self, shape: CitationShape
    ) -> None:
        finding = create_finding_node('the sleep blocks', 'e7').replace_with(
            citation_node=CitationNode(target=shape.citation)
        )

        assert list_item_lines(create_document(finding)) == [
            f'- the sleep blocks {shape.written} [e7]'
        ]

    def test_a_thread_finding_id_is_written_whole(self) -> None:
        finding = create_finding_node('a lead', 'T2.e3')

        assert list_item_lines(create_document(finding)) == ['- a lead [T2.e3]']

    def test_code_spans_in_the_claim_are_written_in_backticks(self) -> None:
        finding = create_finding_node('run `make` first')

        assert list_item_lines(create_document(finding)) == ['- run `make` first [e1]']

    def test_flags_citation_flags_and_notes_are_in_parentheses_in_that_order(self) -> None:
        citation_check = CitationCheck(finding_id='e1', citation='src/a.py:1', state='changed')
        finding = create_finding_node('claim').replace_with(
            citation_node=CitationNode(target='src/a.py:1', citation_check=citation_check),
            lead='1111111',
            notes=(load_wording().write_note('rests_on', 'a page'),),
        )

        (line,) = list_item_lines(create_document(finding))

        expected = '(lead, recorded at 1111111; citation changed; rests on: a page)'
        assert line == f'- claim {expected} `src/a.py:1` [e1]'

    def test_an_finding_with_no_flag_and_no_note_has_no_parentheses(self) -> None:
        (line,) = list_item_lines(create_document(create_finding_node('claim')))

        assert '(' not in line


class TestBlocks:
    def test_points_are_list_lines_without_finding_ids(self) -> None:
        points = PointList(points=(parse_line('a pointer'), parse_line('see `x`')))
        document = Document(title='t', sections=(Section(title='Pointers', blocks=(points,)),))

        assert list_item_lines(document) == ['- a pointer', '- see `x`']

    def test_a_flowchart_is_a_mermaid_code_fence(self) -> None:
        written = Flowchart(lines=('flowchart TD', '  A --> B')).write_markdown()

        assert written == ('```mermaid', 'flowchart TD', '  A --> B', '```')

    def test_the_appendix_follows_the_sections(self) -> None:
        document = Document(
            title='t',
            sections=(Section(title='First', blocks=(Paragraph(line=parse_line('a')),)),),
            appendix=(Section(title='Later', blocks=(Paragraph(line=parse_line('b')),)),),
        )

        headings = [
            line for line in render_markdown(document).splitlines() if line.startswith('## ')
        ]

        assert headings == ['## First', '## Later']


class TestDocumentLayout:
    def test_title_is_a_top_heading_and_the_summary_follows_it(self) -> None:
        text = render_markdown(create_document(title='Why jobs wait'))

        assert text.splitlines()[:3] == ['# Why jobs wait', '', 'Case summary line']

    def test_a_section_is_a_blank_line_a_heading_and_a_blank_line(self) -> None:
        text = render_markdown(create_document(prose=('first sentence',)))

        assert text.splitlines()[3:7] == ['', '## Findings', '', 'first sentence']

    def test_output_ends_with_one_newline(self) -> None:
        text = render_markdown(create_document(create_finding_node('claim')))

        assert text.endswith('[e1]\n')
        assert not text.endswith('\n\n')


BRACKET_POINT = Document(
    title='0',
    sections=(Section(title='0', blocks=(PointList(points=((Text(value=']'),),)),)),),
)


class TestMarkdownWriterProperties:
    @pytest.mark.regression
    @given(document=documents)
    @example(document=BRACKET_POINT)
    def test_every_finding_is_one_line_ending_with_its_finding_id_in_order(
        self, document: Document
    ) -> None:
        findings = [
            finding for section in document.sections for finding in list_section_findings(section)
        ]

        lines = [line for line in list_item_lines(document) if ' [' in line and line.endswith(']')]

        assert [line.rsplit(' [', 1)[1] for line in lines] == [
            f'{finding.finding_id}]' for finding in findings
        ]

    @given(document=documents)
    def test_the_output_ends_with_a_newline(self, document: Document) -> None:
        assert render_markdown(document).endswith('\n')
