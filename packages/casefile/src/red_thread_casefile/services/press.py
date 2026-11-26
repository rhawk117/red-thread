"""The press: writes the board page and the lens outputs of a case file."""

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

import msgspec
from red_thread_core.mentions import MemoryMentionShelf
from red_thread_core.places import BOARD_PAGE
from red_thread_core.writers.markdown import MarkdownWriter

from red_thread_casefile.boards import BoardPage
from red_thread_casefile.lenses import Composer, Edition, Selection, count_lines, get_lens
from red_thread_casefile.policy import get_page_problem
from red_thread_casefile.views import Board
from red_thread_casefile.writers.page import render_case_page

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_core.mentions import MentionShelf
    from red_thread_core.store import PageStore

    from red_thread_casefile.domain import Case
    from red_thread_casefile.lenses import LensName
    from red_thread_casefile.services.casefile import CaseFile


@dataclass(slots=True, kw_only=True, frozen=True)
class ExportRequest:
    lens: LensName
    selection: Selection = field(default_factory=Selection)
    html: bool = False


@dataclass(slots=True, kw_only=True, frozen=True)
class Exported:
    paths: tuple[Path, ...]
    lines: int
    budget: int


@dataclass(slots=True, kw_only=True, frozen=True)
class Press:
    record: CaseFile
    pages: PageStore
    mentions: MentionShelf = field(default_factory=MemoryMentionShelf)

    def gather(self) -> Edition:
        return Edition(
            case=self.record.repository.read_case(),
            ledger=self.record.repository.read_ledger(),
            head=self.record.tree.get_head(),
            findings=self.record.check(),
        )

    def scrub(self, text: str | None) -> str | None:
        if text is None:
            return None
        return self.record.patterns.scrub_text(text)

    def draw(self) -> Path:
        edition = self.gather()
        board = Board(
            case=edition.case,
            ledger=edition.ledger,
            head=edition.head,
            findings=edition.findings,
            plans=self.mentions.list_mentions(edition.case.id),
        )
        document = BoardPage(board=board).compose()
        return self.pages.write(BOARD_PAGE, render_case_page(document))

    def export(self, request: ExportRequest) -> Exported:
        lens = get_lens(request.lens)
        title = self.scrub(request.selection.title)
        selection = replace(request.selection, title=title, goal=self.scrub(request.selection.goal))
        composer = Composer(lens=lens, selection=selection, edition=self.gather())
        if problem := composer.get_selection_problem():
            raise problem

        document = composer.compose()
        text = MarkdownWriter(document=document).render()
        if problem := composer.get_budget_problem(text):
            raise problem

        paths = [self.pages.write(f'out/{lens.name}.md', text)]
        if request.html:
            page = render_case_page(document)
            paths.append(self.pages.write(f'out/{lens.name}.html', page))

        return Exported(paths=tuple(paths), lines=count_lines(text), budget=lens.budget)

    def record_page(self, url: str) -> Case:
        if problem := get_page_problem(url):
            raise problem

        case = msgspec.structs.replace(self.record.repository.read_case(), page_url=url)
        self.record.repository.write_case(case)
        return case
