"""Listing and reading the files under a root, without leaving it and without running its code."""

import os
import shutil
import subprocess
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from red_thread_navigate.walk.domain import (
    MAX_FILE_BYTES,
    SKIPPED_DIRECTORIES,
    SNIFF_BYTES,
    SourceFile,
    Walk,
    tally_skips,
)

if TYPE_CHECKING:
    from red_thread_navigate.walk.domain import SkipKind


def list_tracked(root: Path) -> tuple[str, ...] | None:
    git = shutil.which('git')
    if git is None:
        return None
    command = [git, '-C', str(root), '-c', 'core.fsmonitor=false', 'ls-files', '-z']
    finished = subprocess.run(command, capture_output=True, check=False)  # noqa: S603  the command is git's resolved path with fixed arguments and the root as data
    if finished.returncode != 0:
        return None
    names = finished.stdout.decode('utf-8', errors='surrogateescape').split('\0')
    return tuple(name for name in names if name)


def is_inside(root: Path, path: Path) -> bool:
    return path.resolve().is_relative_to(root)


def keeps_directory(name: str) -> bool:
    return not name.startswith('.') and name not in SKIPPED_DIRECTORIES


def list_directory(root: Path) -> tuple[tuple[str, ...], int]:
    names: list[str] = []
    escaped = 0
    for current, directories, files in os.walk(root, followlinks=False):
        base = Path(current)
        linked = [name for name in directories if base.joinpath(name).is_symlink()]
        escaped += sum(not is_inside(root, base.joinpath(name)) for name in linked)
        directories[:] = [
            name for name in directories if name not in linked and keeps_directory(name)
        ]
        names.extend(base.joinpath(name).relative_to(root).as_posix() for name in files)
    return tuple(names), escaped


def classify(data: bytes) -> SkipKind | None:
    if b'\0' in data[:SNIFF_BYTES]:
        return 'binary'
    try:
        data.decode('utf-8')
    except UnicodeDecodeError:
        return 'not_utf8'
    return None


def read_source(root: Path, path: Path, name: PurePosixPath) -> SourceFile | SkipKind | None:
    if not is_inside(root, path):
        return 'outside_root'
    if not path.resolve().is_file():
        return None
    if path.resolve().stat().st_size > MAX_FILE_BYTES:
        return 'too_large'
    data = path.resolve().read_bytes()
    skipped = classify(data)
    if skipped:
        return skipped
    return SourceFile(path=name, text=data.decode('utf-8'))


def walk(root: Path) -> Walk:
    base = root.resolve()
    if base.is_file():
        names, escaped = ((base.name,), 0)
        base = base.parent
    else:
        tracked = list_tracked(base)
        names, escaped = (tracked, 0) if tracked is not None else list_directory(base)
    reads = [read_source(base, base.joinpath(name), PurePosixPath(name)) for name in sorted(names)]
    files = tuple(read for read in reads if isinstance(read, SourceFile))
    kinds = tuple(read for read in reads if isinstance(read, str))
    skipped = tally_skips((*kinds, *('outside_root',) * escaped))
    return Walk(files=files, skipped=skipped)
