"""Builders for the board page: a board over entries, a finding and a case with a given page."""

from typing import TYPE_CHECKING

from red_thread_casefile.domain import Capabilities, Ledger
from red_thread_casefile.packaged import load_wording
from red_thread_casefile.policy import Finding
from red_thread_casefile.views import Board

from tests.casefile.ledger.builders import create_case
from tests.casefile.ledger.memory import HEAD

if TYPE_CHECKING:
    from red_thread_casefile.domain import Case, Entry
    from red_thread_casefile.policy import CiteState


def create_finding(ref: str, state: CiteState, moved_to: int | None = None) -> Finding:
    return Finding(ref=ref, cite='src/queue.py:3', state=state, moved_to=moved_to)


def create_page_board(
    *entries: Entry,
    head: str | None = HEAD,
    findings: tuple[Finding, ...] = (),
    case: Case | None = None,
) -> Board:
    return Board(
        case=case or create_case(),
        ledger=Ledger(entries=entries),
        head=head,
        findings=findings,
        headings=load_wording().headings,
    )


def create_case_with(*, page_url: str | None = None, languages: tuple[str, ...] = ()) -> Case:
    return create_case().replace_with(
        page_url=page_url, capabilities=Capabilities(languages=languages)
    )
