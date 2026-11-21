"""MarkdownWriter: how an item, its cite and its ref are written."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.views import Document, Item, MarkdownWriter, Section

from tests.casefile.lenses.cases import cite_shape_params
from tests.casefile.pages.builders import create_document

if TYPE_CHECKING:
    from tests.casefile.lenses.cases import CiteShape


def render(document: Document) -> str:
    return MarkdownWriter(document=document).render()


def list_item_lines(document: Document) -> list[str]:
    return [line for line in render(document).splitlines() if line.startswith('- ')]


def cite_shape_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('shape', cite_shape_params())


class TestItemLine:
    @cite_shape_cases()
    def test_item_is_text_then_cite_then_ref_at_the_end_of_the_line(self, shape: CiteShape) -> None:
        document = create_document(Item(text='the sleep blocks', cite=shape.cite, ref='e7'))

        assert list_item_lines(document) == [f'- the sleep blocks {shape.written} [e7]']

    def test_a_thread_ref_is_written_whole(self) -> None:
        document = create_document(Item(text='a lead', ref='T2.e3'))

        assert list_item_lines(document) == ['- a lead [T2.e3]']

    def test_an_item_with_neither_cite_nor_ref_is_just_its_text(self) -> None:
        assert list_item_lines(create_document(Item(text='a pointer'))) == ['- a pointer']

    def test_flags_and_notes_are_in_parentheses_before_the_cite_and_the_ref(self) -> None:
        item = Item(
            text='claim',
            cite='src/a.py:1',
            ref='e1',
            flags=('lead, recorded at 1111111',),
            notes=('rests on: a page',),
        )

        (line,) = list_item_lines(create_document(item))

        assert line.startswith('- claim (')
        assert line.endswith(') `src/a.py:1` [e1]')
        assert 'lead, recorded at 1111111' in line
        assert 'rests on: a page' in line

    def test_an_item_with_no_flag_and_no_note_has_no_parentheses(self) -> None:
        (line,) = list_item_lines(create_document(Item(text='claim', ref='e1')))

        assert '(' not in line


class TestDocumentLayout:
    def test_title_is_a_top_heading_and_the_summary_follows_it(self) -> None:
        text = render(create_document(title='Why jobs wait'))

        assert text.splitlines()[:3] == ['# Why jobs wait', '', 'Case summary line']

    def test_sections_are_second_level_headings_in_document_order(self) -> None:
        document = Document(
            title='t',
            sections=(Section(title='Second', prose=('b',)), Section(title='First', prose=('a',))),
        )

        headings = [line for line in render(document).splitlines() if line.startswith('## ')]

        assert headings == ['## Second', '## First']

    def test_prose_is_written_as_plain_lines_and_not_as_list_items(self) -> None:
        text = render(create_document(prose=('first sentence', 'second sentence')))

        lines = text.splitlines()
        assert 'first sentence' in lines
        assert 'second sentence' in lines
        assert list_item_lines(create_document(prose=('first sentence',))) == []

    def test_output_ends_with_one_newline(self) -> None:
        text = render(create_document(Item(text='claim', ref='e1')))

        assert text.endswith('[e1]\n')
        assert not text.endswith('\n\n')

    @pytest.mark.parametrize('items', [1, 4])
    def test_each_item_is_one_list_line(self, items: int) -> None:
        document = create_document(
            *(Item(text=f'claim {n}', ref=f'e{n}') for n in range(1, items + 1))
        )

        assert len(list_item_lines(document)) == items
