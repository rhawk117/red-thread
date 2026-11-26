"""MarkdownWriter: one line per entry or point, in order, with an entry's cite and ref."""

from itertools import chain
from typing import TYPE_CHECKING

from hypothesis import given
from red_thread_casefile.documents import EntryList, EntryNode, PointList

from tests.casefile.documents.reading import join_line
from tests.casefile.writers.reading import list_item_lines, render_markdown
from tests.casefile.writers.strategies import documents

if TYPE_CHECKING:
    from red_thread_casefile.documents import Block, Citation, Document, Line

type ListItem = EntryNode | Line


def list_block_items(block: Block) -> tuple[ListItem, ...]:
    if isinstance(block, EntryList):
        return block.entries

    if isinstance(block, PointList):
        return block.points

    return ()


def list_document_items(document: Document) -> list[ListItem]:
    blocks = chain.from_iterable(section.blocks for section in document.sections)
    return list(chain.from_iterable(map(list_block_items, blocks)))


def get_claim(item: ListItem) -> Line:
    if isinstance(item, EntryNode):
        return item.claim
    return item


def pair_lines_with_items(document: Document) -> list[tuple[str, ListItem]]:
    return list(zip(list_item_lines(document), list_document_items(document), strict=True))


def list_cite_forms(citation: Citation | None) -> tuple[str, ...]:
    if citation is None:
        return ()
    return (f' <{citation.target}>', f' `{citation.target}`')


def write_point(point: Line) -> str:
    return f'- {join_line(point)}'


class TestMarkdownWriterProperties:
    @given(document=documents)
    def test_every_item_is_one_line_and_the_lines_follow_the_items_in_order(
        self, document: Document
    ) -> None:
        rendered = render_markdown(document)

        item_lines = [line for line in rendered.split('\n') if line.startswith('- ')]
        items = list_document_items(document)
        assert len(item_lines) == len(items)
        assert all(
            line.startswith(f'- {join_line(get_claim(item))}')
            for line, item in zip(item_lines, items, strict=True)
        )
        assert rendered.endswith('\n')

    @given(document=documents)
    def test_an_entry_line_ends_with_its_ref_and_holds_its_cite(self, document: Document) -> None:
        pairs = pair_lines_with_items(document)

        entry_pairs = [(line, item) for line, item in pairs if isinstance(item, EntryNode)]
        for line, entry in entry_pairs:
            assert line.endswith(f' [{entry.ref}]')
            cite_forms = list_cite_forms(entry.citation)
            assert any(form in line for form in cite_forms) == (entry.citation is not None)

    @given(document=documents)
    def test_a_point_line_is_its_text_with_no_cite_and_no_ref(self, document: Document) -> None:
        pairs = pair_lines_with_items(document)

        point_pairs = [(line, item) for line, item in pairs if not isinstance(item, EntryNode)]
        assert [line for line, _ in point_pairs] == [write_point(point) for _, point in point_pairs]
