"""Indexing the readable source files under a path into symbols and references."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_navigate.symbols.domain import Backends, FileSymbols
    from red_thread_navigate.walk import SourceTree


@dataclass(slots=True, kw_only=True, frozen=True)
class Index:
    path: Path
    files: tuple[FileSymbols, ...]
    notes: tuple[str, ...]
    single_file: bool


def index_path(path: Path, *, tree: SourceTree, backends: Backends) -> Index:
    walked = tree.walk(path)
    parsed = tuple(
        backend.parse(source)
        for source in walked.files
        if (backend := backends.for_path(source.path)) is not None
    )
    notes = tuple(note for file in parsed for note in file.notes)
    leading = () if walked.note is None else (walked.note,)
    return Index(path=path, files=parsed, notes=(*leading, *notes), single_file=walked.single_file)
