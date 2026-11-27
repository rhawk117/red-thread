"""The press: writes the board page and the lens outputs of a case file."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import msgspec
from red_thread_core.dto import DTO
from red_thread_core.places import BOARD_PAGE
from red_thread_core.writers.markdown import MarkdownWriter

from red_thread_casefile.boards import BoardPage
from red_thread_casefile.lenses import Composer, Edition, LensName, Selection, count_lines
from red_thread_casefile.views import Board
from red_thread_casefile.writers.page import render_case_page

if TYPE_CHECKING:
    from red_thread_core.documents import Document
    from red_thread_core.store import PageStore

    from red_thread_casefile.lenses import Lens, LensBook
    from red_thread_casefile.services.casefile import CaseFile


class ExportRequest(DTO, frozen=True, kw_only=True, gc=False):
    lens: LensName
    selection: Selection = msgspec.field(default_factory=Selection)
    html: bool = False


class Exported(DTO, frozen=True, kw_only=True, gc=False):
    paths: tuple[Path, ...]
    lines: int
    budget: int


@dataclass(slots=True, kw_only=True, frozen=True)
class Press:
    record: CaseFile
    pages: PageStore
    book: LensBook

    def gather(self) -> Edition:
        record = self.record.load()
        return Edition(
            case=record.case,
            ledger=record.ledger,
            head=self.record.tree.get_head(),
            citation_checks=self.record.find_citations(record.ledger),
        )

    def scrub(self, text: str | None) -> str | None:
        if text is None:
            return None
        return self.record.patterns.scrub_text(text)

    def draw(self) -> Path:
        edition = self.gather()
        wording = self.record.wording
        board = Board(
            case=edition.case,
            ledger=edition.ledger,
            headings=wording.headings,
            head=edition.head,
            citation_checks=edition.citation_checks,
        )
        document = BoardPage(board=board, wording=wording).compose()
        return self.write_page(BOARD_PAGE, document)

    def write_page(self, name: str, document: Document) -> Path:
        return self.pages.write(name, render_case_page(document, self.record.wording.headings))

    def scrub_selection(self, selection: Selection) -> Selection:
        return selection.replace_with(
            title=self.scrub(selection.title), goal=self.scrub(selection.goal)
        )

    def build_composer(self, lens: Lens, selection: Selection) -> Composer:
        return Composer(
            lens=lens,
            selection=selection,
            edition=self.gather(),
            wording=self.record.wording,
            reading=self.book.reading,
        )

    def export(self, request: ExportRequest) -> Exported:
        lens = self.book.get(request.lens)
        composer = self.build_composer(lens, self.scrub_selection(request.selection))
        if problem := composer.get_selection_problem():
            raise problem

        document = composer.compose()
        text = MarkdownWriter(document=document).render()
        if problem := composer.get_budget_problem(text):
            raise problem

        paths = [self.pages.write(f'out/{lens.name}.md', text)]
        if request.html:
            paths.append(self.write_page(f'out/{lens.name}.html', document))

        return Exported(paths=tuple(paths), lines=count_lines(text), budget=lens.budget)
