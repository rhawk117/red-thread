"""An in-memory source tree that behaves like the disk one, for tests that must not touch disk."""

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from red_thread_navigate.walk import PathMissingError, SourceFile, Walk
from red_thread_navigate.walk.domain import tally_skips

if TYPE_CHECKING:
    from red_thread_navigate.walk import SkipKind


def create_memory_root() -> Path:
    return Path('memory')


@dataclass(slots=True, kw_only=True, frozen=True)
class MemoryTree:
    root: Path = field(default_factory=create_memory_root)
    texts: dict[str, str] = field(default_factory=dict)

    def walk(self, root: Path) -> Walk:
        if root != self.root:
            raise PathMissingError(path=root)
        files = tuple(
            SourceFile(path=PurePosixPath(name), text=text)
            for name, text in sorted(self.texts.items())
        )
        return Walk(files=files, skipped=tally_skips(()))

    def read(self, root: Path, name: PurePosixPath) -> SourceFile | SkipKind:
        text = self.texts.get(name.as_posix()) if root == self.root else None
        if text is None:
            return 'not_a_file'
        return SourceFile(path=name, text=text)
