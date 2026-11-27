"""The document tree: notes, lead flags, the findings a section and a document hold, dispatch."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.documents import (
    FindingList,
    list_document_findings,
    list_section_findings,
)
from red_thread_casefile.packaged import load_wording
from red_thread_core.documents import (
    Block,
    Code,
    CodeListing,
    Document,
    Flowchart,
    Link,
    Paragraph,
    PointList,
    Section,
    Text,
    parse_line,
)

from tests.casefile.documents.builders import create_finding_node, create_finding_section
from tests.casefile.documents.fakes import NamingWriter
from tests.params import as_labelled_params, as_params

if TYPE_CHECKING:
    from red_thread_casefile.documents import NoteKind
    from red_thread_core.documents import Inline


@dataclass(slots=True, kw_only=True, frozen=True)
class NoteText:
    name: str
    kind: NoteKind
    text: str
    marks: tuple[pytest.MarkDecorator, ...] = ()


def note_text_cases() -> pytest.MarkDecorator:
    cases = (
        NoteText(name='rests-on', kind='rests_on', text='rests on: a page'),
        NoteText(name='refuted-by', kind='refuted_by', text='refuted by: a page'),
        NoteText(name='retires', kind='retires', text='retires: a page'),
        NoteText(name='retired-by', kind='retired_by', text='retired by a page'),
        NoteText(name='urgency', kind='urgency', text='a page'),
        NoteText(name='source', kind='source', text='a page'),
    )
    return pytest.mark.parametrize('case', as_params(cases))


def inline_dispatch_cases() -> pytest.MarkDecorator:
    nodes: dict[str, Inline] = {
        'text': Text(value='a'),
        'code': Code(value='a'),
        'link': Link(url='a'),
    }
    return pytest.mark.parametrize('node', as_labelled_params(nodes))


def block_dispatch_cases() -> pytest.MarkDecorator:
    blocks: dict[str, Block] = {
        'paragraph': Paragraph(line=parse_line('a')),
        'findings': FindingList(findings=(create_finding_node(),)),
        'points': PointList(points=(parse_line('a'),)),
        'flowchart': Flowchart(lines=('a',)),
        'listing': CodeListing(language='python', source='a'),
    }
    return pytest.mark.parametrize('node', as_labelled_params(blocks))


class TestNote:
    @note_text_cases()
    def test_a_note_reads_as_its_label_then_its_value(self, case: NoteText) -> None:
        assert load_wording().write_note(case.kind, 'a page').text == case.text


class TestFindingNode:
    def test_an_finding_recorded_at_the_board_commit_has_no_flag(self) -> None:
        assert create_finding_node().flags == ()

    def test_an_finding_from_another_commit_is_flagged_as_a_lead(self) -> None:
        assert create_finding_node(lead='1111111').flags == ('lead, recorded at 1111111',)


class TestFindings:
    def test_a_section_holds_the_findings_of_its_lists_in_order(self) -> None:
        section = create_finding_section('e1', 'e2')
        mixed = Section(title='Mixed', blocks=(Paragraph(line=()), *section.blocks))

        assert [finding.finding_id for finding in list_section_findings(mixed)] == ['e1', 'e2']

    def test_a_document_holds_the_findings_of_its_sections_and_not_of_its_appendix(self) -> None:
        document = Document(
            title='A case',
            sections=(create_finding_section('e1'), create_finding_section('e2')),
            appendix=(create_finding_section('e9', title='Retired'),),
        )

        assert [finding.finding_id for finding in list_document_findings(document)] == ['e1', 'e2']


class TestDispatch:
    writer = NamingWriter()

    @inline_dispatch_cases()
    def test_an_inline_reaches_the_method_named_for_its_kind(self, node: Inline) -> None:
        assert node.write(self.writer) == f'{type(node).__name__.lower()} a'

    @block_dispatch_cases()
    def test_every_block_is_a_block_that_writes_html_and_markdown(self, node: Block) -> None:
        assert isinstance(node, Block)

    @block_dispatch_cases()
    def test_a_block_counts_only_the_findings_it_holds(self, node: Block) -> None:
        expected = len(node.findings) if isinstance(node, FindingList) else 0
        assert node.count == expected
