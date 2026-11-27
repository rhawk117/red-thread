"""Builders for the board page: a board over findings, a finding and a case with a given page."""

from typing import TYPE_CHECKING

from red_thread_casefile.domain import Capabilities, CaseLedger
from red_thread_casefile.packaged import load_wording
from red_thread_casefile.policy import CitationCheck
from red_thread_casefile.views import Board

from tests.casefile.ledger.builders import create_case
from tests.casefile.ledger.memory import HEAD

if TYPE_CHECKING:
    from red_thread_casefile.domain import Case, CaseFinding
    from red_thread_casefile.policy import CitationState


def create_citation_check(
    finding_id: str, state: CitationState, moved_to: int | None = None
) -> CitationCheck:
    return CitationCheck(
        finding_id=finding_id, citation='src/queue.py:3', state=state, moved_to=moved_to
    )


def create_page_board(
    *findings: CaseFinding,
    head: str | None = HEAD,
    citation_checks: tuple[CitationCheck, ...] = (),
    case: Case | None = None,
) -> Board:
    return Board(
        case=case or create_case(),
        ledger=CaseLedger(findings=findings),
        head=head,
        citation_checks=citation_checks,
        headings=load_wording().headings,
    )


def create_case_with(*, page_url: str | None = None, languages: tuple[str, ...] = ()) -> Case:
    return create_case().replace_with(
        page_url=page_url, capabilities=Capabilities(languages=languages)
    )
