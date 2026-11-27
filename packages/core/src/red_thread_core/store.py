"""The source tree a citation points into, the clock that stamps a record, the page store."""

import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path


@runtime_checkable
class SourceTree(Protocol):
    def get_head(self) -> str | None: ...

    def list_files(self) -> tuple[str, ...]: ...

    def read_lines(self, path: str) -> tuple[str, ...] | None: ...

    def exclude(self, pattern: str) -> None: ...


@runtime_checkable
class Clock(Protocol):
    def now(self) -> str: ...


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as target:
        target.write(text)


def create_exclusive(path: Path, text: str) -> FileExistsError | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('x', encoding='utf-8') as target:
            target.write(text)
    except FileExistsError as error:
        return error
    return None


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
        append_text(path, f'{gap}{pattern}\n')


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
