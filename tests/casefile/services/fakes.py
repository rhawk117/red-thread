"""A case file wired to memory: the shared in-memory repository framed with one case."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_casefile.domain import Case
from red_thread_casefile.services import CaseFile, Press

from tests.casefile.ledger.memory import (
    HEAD,
    MOMENT,
    FixedClock,
    MemoryCaseRepository,
    MemoryPageStore,
    MemorySourceTree,
)

if TYPE_CHECKING:
    from red_thread_casefile.domain import Entry

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

    @property
    def press(self) -> Press:
        return Press(record=self.case_file, pages=self.pages)

    def read_entries(self) -> tuple[Entry, ...]:
        return self.store.read_ledger().entries

    def seed(self, *entries: Entry) -> None:
        for entry in entries:
            self.store.append(entry.thread, (entry,))


def create_service_harness(files: dict[str, tuple[str, ...]] | None = None) -> ServiceHarness:
    store = MemoryCaseRepository()
    store.create(CASE)
    tree = MemorySourceTree(files=files or {})
    pages = MemoryPageStore()
    case_file = CaseFile(repository=store, tree=tree, clock=FixedClock())
    return ServiceHarness(store=store, tree=tree, pages=pages, case_file=case_file)
