"""Reads back what a DirectoryPageStore wrote, the way a caller opening the file would."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(slots=True, kw_only=True, frozen=True)
class DirectoryPageReader:
    directory: Path

    def read(self, name: str) -> str | None:
        target = self.directory.joinpath(name)
        if not target.is_file():
            return None
        return target.read_text(encoding='utf-8')
