"""MarkdownWriter: one line per finding or point, in order, with a finding's cite and finding id."""

from itertools import chain
from typing import TYPE_CHECKING

from hypothesis import given
from red_thread_casefile.documents import FindingList, FindingNode
from red_thread_core.documents import PointList

from tests.casefile.documents.reading import join_line
from tests.casefile.writers.reading import list_item_lines, render_markdown
from tests.casefile.writers.strategies import documents

if TYPE_CHECKING:
    from red_thread_casefile.documents import CitationNode
    from red_thread_core.documents import Block, Document, Line

type ListItem = FindingNode | Line


def list_block_items(block: Block) -> tuple[ListItem, ...]:
    if isinstance(block, FindingList):
        return block.findings

    if isinstance(block, PointList):
        return block.points

    return ()


def list_document_items(document: Document) -> list[ListItem]:
    blocks = chain.from_iterable(section.blocks for section in document.sections)
    return list(chain.from_iterable(map(list_block_items, blocks)))


def get_claim(item: ListItem) -> Line:
    if isinstance(item, FindingNode):
        return item.claim
    return item


def pair_lines_with_items(document: Document) -> list[tuple[str, ListItem]]:
    return list(zip(list_item_lines(document), list_document_items(document), strict=True))


def list_citation_forms(citation_node: CitationNode | None) -> tuple[str, ...]:
    if citation_node is None:
        return ()
    return (f' <{citation_node.target}>', f' `{citation_node.target}`')


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
    def test_an_finding_line_ends_with_its_finding_id_and_holds_its_citation(
        self, document: Document
    ) -> None:
        pairs = pair_lines_with_items(document)

        finding_pairs = [(line, item) for line, item in pairs if isinstance(item, FindingNode)]
        for line, finding in finding_pairs:
            assert line.endswith(f' [{finding.finding_id}]')
            citation_forms = list_citation_forms(finding.citation_node)
            assert any(form in line for form in citation_forms) == (
                finding.citation_node is not None
            )

    @given(document=documents)
    def test_a_point_line_is_its_text_with_no_citation_and_no_finding_id(
        self, document: Document
    ) -> None:
        pairs = pair_lines_with_items(document)

        point_pairs = [(line, item) for line, item in pairs if not isinstance(item, FindingNode)]
        assert [line for line, _ in point_pairs] == [write_point(point) for _, point in point_pairs]
