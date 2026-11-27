"""A case file wired to memory: the shared in-memory repository framed with one case."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_casefile.domain import Case
from red_thread_casefile.packaged import load_lens_book, load_wording
from red_thread_casefile.services import CaseFile, Press

from tests.casefile.ledger.markdown import CaseScribe
from tests.casefile.ledger.memory import (
    HEAD,
    MemoryCaseRepository,
    MemoryPageStore,
    MemorySourceTree,
)
from tests.codec import YAML
from tests.core.timekeeping.clock import MOMENT, FixedClock

if TYPE_CHECKING:
    from red_thread_casefile.domain import CaseFinding

CASE = Case(
    id='20261121-properties',
    target='what holds for every input',
    kind='claim',
    bar='every claim is cited',
    created=MOMENT,
    head=HEAD,
)


@dataclass(slots=True, kw_only=True, frozen=True)
class ServiceHarness:
    store: MemoryCaseRepository
    tree: MemorySourceTree
    pages: MemoryPageStore
    case_file: CaseFile
    scribe: CaseScribe

    @property
    def press(self) -> Press:
        return Press(record=self.case_file, pages=self.pages, book=load_lens_book())

    def read_findings(self) -> tuple[CaseFinding, ...]:
        return self.case_file.load().ledger.findings

    def seed(self, *findings: CaseFinding) -> None:
        for finding in findings:
            self.scribe.seed(finding.thread, finding)


def create_service_harness(files: dict[str, tuple[str, ...]] | None = None) -> ServiceHarness:
    store = MemoryCaseRepository()
    scribe = CaseScribe(sink=store, cases=[CASE])
    scribe.frame(CASE)
    tree = MemorySourceTree(files=files or {})
    pages = MemoryPageStore()
    case_file = CaseFile(
        repository=store, tree=tree, clock=FixedClock(), wording=load_wording(), codec=YAML
    )
    return ServiceHarness(store=store, tree=tree, pages=pages, case_file=case_file, scribe=scribe)
