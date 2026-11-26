"""In-memory stand-ins for the case file's three ports, behaving like their real adapters."""

from dataclasses import dataclass, field
from pathlib import Path

from red_thread_casefile.domain import CASE_FILE, LedgerSource
from red_thread_casefile.errors import CaseExistsError, CaseNotFoundError
from red_thread_casefile.store import order_thread_file

MOMENT = '2026-11-21T09:30:00+00:00'
DAY = '2026-11-21'
HEAD = '1111111111111111111111111111111111111111'
SHORT_HEAD = HEAD[:7]
NEXT_HEAD = '2222222222222222222222222222222222222222'
MEMORY_CASE = 'memory'


def start_heads() -> list[str | None]:
    return [HEAD]


def name_thread(name: str) -> str | None:
    return None if name == CASE_FILE else Path(name).stem


def order_file(name: str) -> tuple[bool, bool, int, str]:
    return (name != CASE_FILE, *order_thread_file(Path(name)))


@dataclass(slots=True, kw_only=True, frozen=True)
class MemoryCaseRepository:
    files: dict[str, str] = field(default_factory=dict)

    def exists(self) -> bool:
        return CASE_FILE in self.files

    def create(self, text: str) -> None:
        if self.exists():
            raise CaseExistsError(case_id=MEMORY_CASE)
        self.files[CASE_FILE] = text

    def read(self) -> tuple[LedgerSource, ...]:
        if not self.exists():
            raise CaseNotFoundError(path=Path(MEMORY_CASE))
        names = sorted(self.files, key=order_file)
        return tuple(
            LedgerSource(name=name, thread=name_thread(name), text=self.files[name])
            for name in names
        )

    def write(self, name: str, text: str) -> None:
        self.files[name] = text


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
