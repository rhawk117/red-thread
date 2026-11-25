"""In-memory stand-ins for the case file's three ports, behaving like their real adapters."""

from collections import defaultdict
from dataclasses import dataclass, field
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING

from msgspec.structs import replace
from red_thread_casefile.domain import Ledger, order_thread
from red_thread_casefile.errors import CaseNotFoundError

if TYPE_CHECKING:
    from red_thread_casefile.domain import Case, Entry

MOMENT = '2026-11-21T09:30:00+00:00'
HEAD = '1111111111111111111111111111111111111111'
NEXT_HEAD = '2222222222222222222222222222222222222222'


def start_heads() -> list[str | None]:
    return [HEAD]


def start_thread_files() -> defaultdict[str | None, list[Entry]]:
    return defaultdict(list)


@dataclass(slots=True, kw_only=True, frozen=True)
class MemoryCaseRepository:
    cases: list[Case] = field(default_factory=list)
    files: defaultdict[str | None, list[Entry]] = field(default_factory=start_thread_files)

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
        self.files[thread].extend(replace(entry, thread=thread) for entry in entries)


@dataclass(slots=True, kw_only=True, frozen=True)
class MemorySourceTree:
    files: dict[str, tuple[str, ...]] = field(default_factory=dict)
    heads: list[str | None] = field(default_factory=start_heads)
    reads: list[str] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)

    def get_head(self) -> str | None:
        return self.heads[-1]

    def list_files(self) -> tuple[str, ...]:
        return tuple(self.files)

    def read_lines(self, path: str) -> tuple[str, ...] | None:
        self.reads.append(path)
        return self.files.get(path)

    def exclude(self, pattern: str) -> None:
        self.exclusions.append(pattern)

    def write(self, path: str, lines: tuple[str, ...]) -> None:
        self.files[path] = lines

    def remove(self, path: str) -> None:
        self.files.pop(path, None)

    def advance(self, head: str | None) -> None:
        self.heads.append(head)


@dataclass(slots=True, kw_only=True, frozen=True)
class MemoryPageStore:
    files: dict[str, str] = field(default_factory=dict)
    root: Path = Path('memory')

    def write(self, name: str, text: str) -> Path:
        self.files[name] = text
        return self.root.joinpath(name)

    def read(self, name: str) -> str | None:
        return self.files.get(name)


@dataclass(slots=True, kw_only=True, frozen=True)
class FixedClock:
    moment: str = MOMENT

    def now(self) -> str:
        return self.moment
