"""Indexing the readable source files under a path into symbols and references."""

from pathlib import Path
from typing import TYPE_CHECKING

from red_thread_core.dto import DTO

from red_thread_navigate.symbols.domain import FileSymbols

if TYPE_CHECKING:
    from red_thread_navigate.symbols.domain import Backends
    from red_thread_navigate.walk import SourceTree


class Index(DTO, frozen=True, kw_only=True, gc=False):
    path: Path
    files: tuple[FileSymbols, ...]
    notes: tuple[str, ...]
    single_file: bool


def index_path(path: Path, *, tree: SourceTree, backends: Backends) -> Index:
    walked = tree.walk(path)
    parsed = tuple(
        backend.parse(source)
        for source in walked.files
        if (backend := backends.for_path(source.path))
    )
    notes = tuple(note for file in parsed for note in file.notes)
    leading = () if walked.note is None else (walked.note,)
    return Index(path=path, files=parsed, notes=(*leading, *notes), single_file=walked.single_file)
