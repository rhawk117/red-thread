"""Indexing the readable source files under a path into symbols and references."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_navigate.symbols.store import backend_for
from red_thread_navigate.walk import walk

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_navigate.symbols.domain import FileSymbols


@dataclass(slots=True, kw_only=True, frozen=True)
class Index:
    files: tuple[FileSymbols, ...]
    notes: tuple[str, ...]


def index_path(path: Path) -> Index:
    walked = walk(path)
    parsed = tuple(
        backend.parse(source)
        for source in walked.files
        if (backend := backend_for(source.path)) is not None
    )
    notes = tuple(note for file in parsed for note in file.notes)
    leading = () if walked.note is None else (walked.note,)
    return Index(files=parsed, notes=(*leading, *notes))
