"""Where a case lives on disk: its record and its ledgers."""

from dataclasses import dataclass
from itertools import chain
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from red_thread_core.store import append_text

from red_thread_casefile.domain import THREAD_NAME, Ledger, order_thread
from red_thread_casefile.errors import CaseNotFoundError, CorruptCaseError, CorruptLedgerError
from red_thread_casefile.schemas import case_from_text, case_to_text, entry_from_line, entry_to_line

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_casefile.domain import Case, Entry


@runtime_checkable
class CaseRepository(Protocol):
    def exists(self) -> bool: ...

    def create(self, case: Case) -> None: ...

    def read_case(self) -> Case: ...

    def write_case(self, case: Case) -> None: ...

    def read_ledger(self) -> Ledger: ...

    def append(self, thread: str | None, entries: tuple[Entry, ...]) -> None: ...


@dataclass(slots=True, kw_only=True, frozen=True)
class LedgerLine:
    path: Path
    number: int
    text: str
    thread: str | None

    def parse(self) -> Entry:
        try:
            return entry_from_line(self.text, self.thread)
        except (ValueError, TypeError) as error:
            raise CorruptLedgerError(path=self.path, line_number=self.number) from error


@dataclass(slots=True, kw_only=True, frozen=True)
class LedgerFiles:
    directory: Path

    def locate(self, thread: str | None) -> Path:
        if thread is None:
            return self.directory.joinpath('ledger.jsonl')
        return self.directory.joinpath('threads', f'{thread}.jsonl')

    def list_threads(self) -> tuple[str, ...]:
        stems = (path.stem for path in self.directory.joinpath('threads').glob('T*.jsonl'))
        names = (stem for stem in stems if THREAD_NAME.fullmatch(stem))
        return tuple(sorted(names, key=order_thread))

    def read(self, thread: str | None) -> tuple[Entry, ...]:
        path = self.locate(thread)
        if not path.is_file():
            return ()
        numbered = enumerate(path.read_text(encoding='utf-8').split('\n'), 1)
        lines = (
            LedgerLine(path=path, number=number, text=text, thread=thread)
            for number, text in numbered
            if text.strip()
        )
        return tuple(line.parse() for line in lines)

    def read_all(self) -> Ledger:
        files = (None, *self.list_threads())
        return Ledger(entries=tuple(chain.from_iterable(map(self.read, files))))

    def append(self, thread: str | None, entries: tuple[Entry, ...]) -> None:
        lines = ''.join(f'{entry_to_line(entry)}\n' for entry in entries)
        append_text(self.locate(thread), lines)


@dataclass(slots=True, kw_only=True, frozen=True)
class DirectoryCaseRepository:
    directory: Path

    @property
    def case_file(self) -> Path:
        return self.directory.joinpath('case.json')

    @property
    def ledgers(self) -> LedgerFiles:
        return LedgerFiles(directory=self.directory)

    def exists(self) -> bool:
        return self.case_file.is_file()

    def create(self, case: Case) -> None:
        self.directory.joinpath('threads').mkdir(parents=True, exist_ok=True)
        self.write_case(case)

    def get_case_problem(self) -> CaseNotFoundError | None:
        if self.exists():
            return None
        return CaseNotFoundError(path=self.directory)

    def read_case(self) -> Case:
        if problem := self.get_case_problem():
            raise problem
        try:
            return case_from_text(self.case_file.read_text(encoding='utf-8'))
        except ValueError as error:
            raise CorruptCaseError(path=self.case_file, reason=str(error)) from error

    def write_case(self, case: Case) -> None:
        self.case_file.write_text(case_to_text(case), encoding='utf-8')

    def read_ledger(self) -> Ledger:
        if problem := self.get_case_problem():
            raise problem
        return self.ledgers.read_all()

    def append(self, thread: str | None, entries: tuple[Entry, ...]) -> None:
        self.ledgers.append(thread, entries)
