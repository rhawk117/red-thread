"""The board's document: the case map of the whole ledger, and the diagram carried to each item."""

from typing import TYPE_CHECKING

from red_thread_casefile.boards import BoardPage
from red_thread_casefile.domain import Ledger
from red_thread_casefile.lenses import Composer, Edition, Plan, get_lens
from red_thread_casefile.views import Board

from tests.casefile.charts.reading import read_map
from tests.casefile.ledger.builders import create_case, create_entry
from tests.casefile.ledger.memory import HEAD

if TYPE_CHECKING:
    from red_thread_casefile.domain import Entry
    from red_thread_casefile.views import Document

DIAGRAM = 'flowchart TD\n  A --> B'


def create_board(*entries: Entry) -> Board:
    return Board(case=create_case(), ledger=Ledger(entries=entries), head=HEAD)


def list_item_diagrams(document: Document) -> list[str | None]:
    return [item.diagram for section in document.sections for item in section.items]


class TestBoardMap:
    def test_the_document_holds_the_map_of_every_entry_retired_ones_included(self) -> None:
        board = create_board(
            create_entry(seq=1, kind='open', text='stale'),
            create_entry(seq=2, kind='open', text='fresh', supersedes=('e1',)),
            create_entry(seq=1, thread='T1', kind='known', text='deep'),
        )

        drawn = read_map(BoardPage(board=board).compose().map_lines)

        assert [node.label.split(':')[0] for node in drawn.nodes] == [
            'e1 open',
            'e2 open',
            'T1.e1 known',
        ]
        assert [node.style for node in drawn.nodes] == ['k_retired', 'k_open', 'k_known']
        assert len(drawn.retirements) == 1

    def test_an_empty_ledger_has_no_map_lines(self) -> None:
        assert BoardPage(board=create_board()).compose().map_lines == ()


class TestDiagramOnItems:
    def test_the_board_document_carries_each_entry_diagram_and_none_when_it_has_none(self) -> None:
        board = create_board(
            create_entry(seq=1, kind='known', text='a', diagram=DIAGRAM),
            create_entry(seq=2, kind='known', text='b'),
        )

        assert list_item_diagrams(BoardPage(board=board).compose()) == [DIAGRAM, None]

    def test_the_text_board_does_not_show_a_diagram(self) -> None:
        board = create_board(create_entry(seq=1, kind='known', text='a', diagram=DIAGRAM))
        plain = create_board(create_entry(seq=1, kind='known', text='a'))

        assert board.render() == plain.render()
        assert 'flowchart' not in board.render()


class TestLensDocument:
    def create_composer(self, *entries: Entry) -> Composer:
        edition = Edition(case=create_case(), ledger=Ledger(entries=entries), head=HEAD)
        return Composer(lens=get_lens('brief'), plan=Plan(), edition=edition)

    def test_a_lens_document_leaves_the_map_empty(self) -> None:
        composer = self.create_composer(create_entry(seq=1, kind='open', text='a question'))

        assert composer.compose().map_lines == ()

    def test_a_lens_document_carries_each_entry_diagram(self) -> None:
        composer = self.create_composer(
            create_entry(seq=1, kind='open', text='a question', diagram=DIAGRAM)
        )

        assert DIAGRAM in list_item_diagrams(composer.compose())
