"""The board's document: the case map of the whole ledger, and the diagram carried to each item."""

from typing import TYPE_CHECKING

from red_thread_casefile.boards import BoardPage
from red_thread_casefile.documents import list_document_findings
from red_thread_casefile.domain import CaseLedger
from red_thread_casefile.lenses import Composer, Edition, Selection
from red_thread_casefile.packaged import load_lens_book, load_wording
from red_thread_casefile.views import Board
from red_thread_core.documents import Flowchart

from tests.casefile.charts.reading import read_map
from tests.casefile.ledger.builders import create_case, create_finding
from tests.casefile.ledger.memory import HEAD

if TYPE_CHECKING:
    from red_thread_casefile.domain import CaseFinding
    from red_thread_core.documents import Document

DIAGRAM = 'flowchart TD\n  A --> B'


def create_board(*findings: CaseFinding) -> Board:
    return Board(
        case=create_case(),
        ledger=CaseLedger(findings=findings),
        head=HEAD,
        headings=load_wording().headings,
    )


def list_item_diagrams(document: Document) -> list[str | None]:
    return [finding.diagram for finding in list_document_findings(document)]


def list_map_lines(document: Document) -> tuple[str, ...]:
    blocks = (block for section in document.appendix for block in section.blocks)
    chart = next((block for block in blocks if isinstance(block, Flowchart)), None)
    if chart is None:
        return ()
    return chart.lines[1:]


class TestBoardMap:
    def test_the_document_holds_the_map_of_every_finding_retired_ones_included(self) -> None:
        board = create_board(
            create_finding(finding_number=1, kind='open', text='stale'),
            create_finding(finding_number=2, kind='open', text='fresh', supersedes=('e1',)),
            create_finding(finding_number=1, thread='T1', kind='known', text='deep'),
        )

        drawn = read_map(list_map_lines(BoardPage(board=board, wording=load_wording()).compose()))

        assert [node.label.split(':')[0] for node in drawn.nodes] == [
            'e1 open',
            'e2 open',
            'T1.e1 known',
        ]
        assert [node.style for node in drawn.nodes] == ['k_retired', 'k_open', 'k_known']
        assert len(drawn.retirements) == 1

    def test_an_empty_ledger_has_no_map_lines(self) -> None:
        assert (
            list_map_lines(BoardPage(board=create_board(), wording=load_wording()).compose()) == ()
        )


class TestDiagramOnItems:
    def test_the_board_document_carries_each_finding_diagram_and_none_when_it_has_none(
        self,
    ) -> None:
        board = create_board(
            create_finding(finding_number=1, kind='known', text='a', diagram=DIAGRAM),
            create_finding(finding_number=2, kind='known', text='b'),
        )

        assert list_item_diagrams(BoardPage(board=board, wording=load_wording()).compose()) == [
            DIAGRAM,
            None,
        ]

    def test_the_text_board_does_not_show_a_diagram(self) -> None:
        board = create_board(
            create_finding(finding_number=1, kind='known', text='a', diagram=DIAGRAM)
        )
        plain = create_board(create_finding(finding_number=1, kind='known', text='a'))

        assert board.render() == plain.render()
        assert 'flowchart' not in board.render()


class TestLensDocument:
    def create_composer(self, *findings: CaseFinding) -> Composer:
        edition = Edition(case=create_case(), ledger=CaseLedger(findings=findings), head=HEAD)
        return Composer(
            lens=load_lens_book().get('brief'),
            selection=Selection(),
            edition=edition,
            wording=load_wording(),
            reading=load_lens_book().reading,
        )

    def test_a_lens_document_leaves_the_map_empty(self) -> None:
        composer = self.create_composer(
            create_finding(finding_number=1, kind='open', text='a question')
        )

        assert list_map_lines(composer.compose()) == ()

    def test_a_lens_document_carries_each_finding_diagram(self) -> None:
        composer = self.create_composer(
            create_finding(finding_number=1, kind='open', text='a question', diagram=DIAGRAM)
        )

        assert DIAGRAM in list_item_diagrams(composer.compose())
