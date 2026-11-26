"""MarkdownWriter: the order of the sections, prose lines and one list line per entry."""

import pytest
from red_thread_core.documents import Document, Paragraph, Section, parse_line

from tests.casefile.writers.builders import create_document, create_entry_node
from tests.casefile.writers.reading import list_item_lines, render_markdown


def create_prose_section(title: str, text: str) -> Section:
    return Section(title=title, blocks=(Paragraph(line=parse_line(text)),))


def entry_count_cases() -> pytest.MarkDecorator:
    counts = [pytest.param(1, id='one-entry'), pytest.param(4, id='four-entries')]
    return pytest.mark.parametrize('entries', counts)


class TestDocumentLayout:
    def test_sections_are_second_level_headings_in_document_order(self) -> None:
        document = Document(
            title='t',
            sections=(create_prose_section('Second', 'b'), create_prose_section('First', 'a')),
        )

        headings = [
            line for line in render_markdown(document).splitlines() if line.startswith('## ')
        ]

        assert headings == ['## Second', '## First']

    def test_prose_is_written_as_plain_lines_and_not_as_list_items(self) -> None:
        text = render_markdown(create_document(prose=('first sentence', 'second sentence')))

        lines = text.splitlines()
        assert 'first sentence' in lines
        assert 'second sentence' in lines
        assert list_item_lines(create_document(prose=('first sentence',))) == []

    @entry_count_cases()
    def test_each_entry_is_one_list_line(self, entries: int) -> None:
        document = create_document(
            *(create_entry_node(f'claim {n}', f'e{n}') for n in range(1, entries + 1))
        )

        assert len(list_item_lines(document)) == entries
