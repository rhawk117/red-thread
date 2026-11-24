"""Where a case lives on disk, the tree its citations point into and the clock that stamps it."""

import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import chain
from typing import TYPE_CHECKING, Protocol, runtime_checkable

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


@runtime_checkable
class SourceTree(Protocol):
    def get_head(self) -> str | None: ...

    def list_files(self) -> tuple[str, ...]: ...

    def read_lines(self, path: str) -> tuple[str, ...] | None: ...

    def exclude(self, pattern: str) -> None: ...


@runtime_checkable
class Clock(Protocol):
    def now(self) -> str: ...


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
        path = self.locate(thread)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = ''.join(f'{entry_to_line(entry)}\n' for entry in entries)
        with path.open('a', encoding='utf-8') as ledger:
            ledger.write(lines)


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

    def read_case(self) -> Case:
        if not self.exists():
            raise CaseNotFoundError(path=self.directory)
        try:
            return case_from_text(self.case_file.read_text(encoding='utf-8'))
        except ValueError as error:
            raise CorruptCaseError(path=self.case_file, reason=str(error)) from error

    def write_case(self, case: Case) -> None:
        self.case_file.write_text(case_to_text(case), encoding='utf-8')

    def read_ledger(self) -> Ledger:
        if not self.exists():
            raise CaseNotFoundError(path=self.directory)
        return self.ledgers.read_all()

    def append(self, thread: str | None, entries: tuple[Entry, ...]) -> None:
        self.ledgers.append(thread, entries)


@dataclass(slots=True, kw_only=True, frozen=True)
class GitSourceTree:
    root: Path

    def run_git(self, *arguments: str) -> str | None:
        git = shutil.which('git')
        if git is None:
            return None
        command = [git, '-C', str(self.root), *arguments]
        finished = subprocess.run(command, capture_output=True, text=True, check=False)  # noqa: S603  the command is git's resolved path with fixed arguments, and no ledger text reaches it
        if finished.returncode != 0:
            return None
        return finished.stdout.strip()

    def get_head(self) -> str | None:
        return self.run_git('rev-parse', 'HEAD') or None

    def list_files(self) -> tuple[str, ...]:
        return tuple((self.run_git('ls-files') or '').splitlines())

    def read_lines(self, path: str) -> tuple[str, ...] | None:
        target = self.root.joinpath(path)
        if not target.is_file():
            return None
        text = target.read_text(encoding='utf-8', errors='replace')
        if not text:
            return ()
        return tuple(text.removesuffix('\n').split('\n'))

    def exclude(self, pattern: str) -> None:
        located = self.run_git('rev-parse', '--git-path', 'info/exclude')
        if located is None:
            return
        path = self.root.joinpath(located)
        existing = path.read_text(encoding='utf-8') if path.is_file() else ''
        if pattern in existing.split('\n'):
            return
        gap = '\n' if existing and not existing.endswith('\n') else ''
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf-8') as exclusions:
            exclusions.write(f'{gap}{pattern}\n')


@dataclass(slots=True, kw_only=True, frozen=True)
class SystemClock:
    precision: str = 'seconds'

    def now(self) -> str:
        return datetime.now(UTC).isoformat(timespec=self.precision)


@runtime_checkable
class PageStore(Protocol):
    def write(self, name: str, text: str) -> Path: ...


@dataclass(slots=True, kw_only=True, frozen=True)
class DirectoryPageStore:
    directory: Path

    def write(self, name: str, text: str) -> Path:
        target = self.directory.joinpath(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')
        return target
