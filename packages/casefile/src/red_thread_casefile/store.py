"""Where a case lives on disk: case.md, and one Markdown file per thread under threads/."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from red_thread_casefile.domain import (
    CASE_FILE,
    THREAD_HOME,
    THREAD_NAME,
    THREAD_SUFFIX,
    LedgerSource,
    order_thread,
)
from red_thread_casefile.errors import CaseExistsError, CaseNotFoundError, UndecodableFileError

if TYPE_CHECKING:
    from pathlib import Path

UNNUMBERED = 0


@runtime_checkable
class CaseRepository(Protocol):
    def exists(self) -> bool: ...

    def create(self, text: str) -> None: ...

    def read(self) -> tuple[LedgerSource, ...]: ...


def order_thread_file(path: Path) -> tuple[bool, int, str]:
    numbered = THREAD_NAME.fullmatch(path.stem) is not None
    number = order_thread(path.stem) if numbered else UNNUMBERED
    return (not numbered, number, path.name)


@dataclass(slots=True, kw_only=True, frozen=True)
class DirectoryCaseRepository:
    directory: Path

    @property
    def case_file(self) -> Path:
        return self.directory.joinpath(CASE_FILE)

    @property
    def thread_home(self) -> Path:
        return self.directory.joinpath(THREAD_HOME)

    def exists(self) -> bool:
        return self.case_file.is_file()

    def create(self, text: str) -> None:
        self.thread_home.mkdir(parents=True, exist_ok=True)
        try:
            with self.case_file.open('x', encoding='utf-8') as target:
                target.write(text)
        except FileExistsError as error:
            raise CaseExistsError(case_id=self.directory.name) from error

    def read_source(self, path: Path) -> LedgerSource:
        name = path.relative_to(self.directory).as_posix()
        thread = None if path == self.case_file else path.stem
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError as error:
            raise UndecodableFileError(path=path) from error
        return LedgerSource(name=name, thread=thread, text=text)

    def list_files(self) -> tuple[Path, ...]:
        threads = sorted(self.thread_home.glob(f'*{THREAD_SUFFIX}'), key=order_thread_file)
        return (self.case_file, *threads)

    def read(self) -> tuple[LedgerSource, ...]:
        if not self.exists():
            raise CaseNotFoundError(path=self.directory)
        return tuple(map(self.read_source, self.list_files()))
