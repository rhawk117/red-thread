"""The document tree: notes, lead flags, the entries a section and a document hold, dispatch."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.documents import (
    Code,
    Document,
    EntryList,
    Flowchart,
    Link,
    Note,
    Paragraph,
    PointList,
    Section,
    Text,
    parse_line,
)

from tests.casefile.documents.builders import create_entry_node, create_entry_section
from tests.casefile.documents.fakes import NamingWriter
from tests.params import as_labelled_params, as_params

if TYPE_CHECKING:
    from red_thread_casefile.documents import Block, Inline, NoteKind


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
        'entries': EntryList(entries=(create_entry_node(),)),
        'points': PointList(points=(parse_line('a'),)),
        'flowchart': Flowchart(lines=('a',)),
    }
    return pytest.mark.parametrize('node', as_labelled_params(blocks))


class TestNote:
    @note_text_cases()
    def test_a_note_reads_as_its_label_then_its_value(self, case: NoteText) -> None:
        assert Note(kind=case.kind, value='a page').text == case.text


class TestEntryNode:
    def test_an_entry_recorded_at_the_board_commit_has_no_flag(self) -> None:
        assert create_entry_node().flags == ()

    def test_an_entry_from_another_commit_is_flagged_as_a_lead(self) -> None:
        assert create_entry_node(lead='1111111').flags == ('lead, recorded at 1111111',)


class TestEntries:
    def test_a_section_holds_the_entries_of_its_lists_in_order(self) -> None:
        section = create_entry_section('e1', 'e2')
        mixed = Section(title='Mixed', blocks=(Paragraph(line=()), *section.blocks))

        assert [entry.ref for entry in mixed.entries] == ['e1', 'e2']

    def test_a_document_holds_the_entries_of_its_sections_and_not_of_its_appendix(self) -> None:
        document = Document(
            title='A case',
            sections=(create_entry_section('e1'), create_entry_section('e2')),
            appendix=(create_entry_section('e9', title='Retired'),),
        )

        assert [entry.ref for entry in document.entries] == ['e1', 'e2']


class TestDispatch:
    writer = NamingWriter()

    @inline_dispatch_cases()
    def test_an_inline_reaches_the_method_named_for_its_kind(self, node: Inline) -> None:
        assert node.write(self.writer) == f'{type(node).__name__.lower()} a'

    @block_dispatch_cases()
    def test_a_block_reaches_the_method_named_for_its_kind(self, node: Block) -> None:
        name = type(node).__name__.lower().replace('entrylist', 'entries')
        name = name.replace('pointlist', 'points')
        assert node.write(self.writer).startswith(f'{name} ')
