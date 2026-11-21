"""A case file wired to memory: a ledger store that copies entries the way the real one does."""

from dataclasses import dataclass, field
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING

import msgspec
from red_thread_casefile.domain import Case, Entry, Ledger, order_thread
from red_thread_casefile.errors import CaseNotFoundError
from red_thread_casefile.services import CaseFile, Press

from tests.casefile.ledger.memory import (
    HEAD,
    MOMENT,
    FixedClock,
    MemoryPageStore,
    MemorySourceTree,
)

if TYPE_CHECKING:
    from red_thread_casefile.domain import EntryKind

CASE = Case(
    id='20261121-properties',
    target='what holds for every input',
    kind='claim',
    bar='every claim is cited',
    created=MOMENT,
    head=HEAD,
)


@dataclass(slots=True, kw_only=True, frozen=True)
class LedgerStore:
    cases: list[Case] = field(default_factory=list)
    files: dict[str | None, list[Entry]] = field(default_factory=dict)

    def exists(self) -> bool:
        return bool(self.cases)

    def create(self, case: Case) -> None:
        self.write_case(case)

    def read_case(self) -> Case:
        if not self.exists():
            raise CaseNotFoundError(path=Path('memory'))
        return self.cases[-1]

    def write_case(self, case: Case) -> None:
        self.cases[:] = [case]

    def read_ledger(self) -> Ledger:
        if not self.exists():
            raise CaseNotFoundError(path=Path('memory'))
        threads = sorted((name for name in self.files if name is not None), key=order_thread)
        held = (self.files.get(name, []) for name in (None, *threads))
        return Ledger(entries=tuple(chain.from_iterable(held)))

    def append(self, thread: str | None, entries: tuple[Entry, ...]) -> None:
        kept = self.files.setdefault(thread, [])
        kept.extend(msgspec.structs.replace(entry, thread=thread) for entry in entries)


@dataclass(slots=True, kw_only=True, frozen=True)
class ServiceHarness:
    store: LedgerStore
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


def create_entry(
    *,
    seq: int,
    thread: str | None = None,
    kind: EntryKind = 'open',
    text: str = 'a finding',
    supersedes: tuple[str, ...] = (),
    head: str | None = HEAD,
) -> Entry:
    return Entry(
        seq=seq,
        round=1,
        kind=kind,
        text=text,
        source='scout',
        at=MOMENT,
        head=head,
        supersedes=supersedes,
        thread=thread,
    )


def create_service_harness(files: dict[str, tuple[str, ...]] | None = None) -> ServiceHarness:
    store = LedgerStore()
    store.create(CASE)
    tree = MemorySourceTree(files=files or {})
    pages = MemoryPageStore()
    case_file = CaseFile(repository=store, tree=tree, clock=FixedClock())
    return ServiceHarness(store=store, tree=tree, pages=pages, case_file=case_file)
