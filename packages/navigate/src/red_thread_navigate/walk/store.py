"""Listing and reading the files under a root, without leaving it and without running its code."""

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from red_thread_navigate.walk.domain import (
    MAX_FILE_BYTES,
    SKIPPED_DIRECTORIES,
    SNIFF_BYTES,
    SourceFile,
    TrackedFiles,
    Walk,
    tally_skips,
)
from red_thread_navigate.walk.errors import PathMissingError

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_navigate.walk.domain import SkipKind, SkipTally


def run_git(git: str, root: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    command = [git, '-C', str(root), '-c', 'core.fsmonitor=false', *arguments]
    environment = {**os.environ, 'LC_ALL': 'C'}
    return subprocess.run(command, capture_output=True, check=False, env=environment)  # noqa: S603  the command is git's resolved path with fixed arguments and the root as data


def is_outside_work_tree(git: str, root: Path) -> bool:
    finished = run_git(git, root, 'rev-parse', '--is-inside-work-tree')
    if finished.returncode == 0:
        return finished.stdout.strip() != b'true'
    return b'not a git repository' in finished.stderr


def list_tracked(root: Path) -> TrackedFiles:
    git = shutil.which('git')
    if git is None:
        return TrackedFiles(names=None)
    finished = run_git(git, root, 'ls-files', '-z')
    if finished.returncode != 0:
        return TrackedFiles(names=None, failed=not is_outside_work_tree(git, root))
    names = finished.stdout.decode('utf-8', errors='surrogateescape').split('\0')
    return TrackedFiles(names=tuple(filter(None, names)))


def keeps_directory(name: str) -> bool:
    return not name.startswith('.') and name not in SKIPPED_DIRECTORIES


def list_directory(root: Path) -> tuple[tuple[str, ...], int]:
    names: list[str] = []
    errors: list[OSError] = []
    for current, directories, files in root.walk(on_error=errors.append):
        directories[:] = filter(keeps_directory, directories)
        names.extend(current.joinpath(name).relative_to(root).as_posix() for name in files)
    return tuple(names), len(errors)


def read_limited(target: Path) -> bytes | SkipKind:
    try:
        if not target.is_file():
            return 'not_a_file'
        if target.stat().st_size > MAX_FILE_BYTES:
            return 'too_large'
        return target.read_bytes()
    except OSError:
        return 'unreadable'


def decode_source(name: PurePosixPath, data: bytes) -> SourceFile | SkipKind:
    if b'\0' in data[:SNIFF_BYTES]:
        return 'binary'
    try:
        return SourceFile(path=name, text=data.decode('utf-8'))
    except UnicodeDecodeError:
        return 'not_utf8'


def read_source(root: Path, path: Path, name: PurePosixPath) -> SourceFile | SkipKind:
    target = path.resolve()
    if not target.is_relative_to(root):
        return 'outside_root'
    data = read_limited(target)
    if isinstance(data, str):
        return data
    return decode_source(name, data)


def list_names(base: Path) -> tuple[tuple[str, ...], int, bool]:
    if base.is_file():
        return (base.name,), 0, False
    tracked = list_tracked(base)
    if tracked.names is not None:
        return tracked.names, 0, tracked.failed
    names, unreadable = list_directory(base)
    return names, unreadable, tracked.failed


def split_reads(
    base: Path, names: tuple[str, ...], unreadable: int
) -> tuple[tuple[SourceFile, ...], SkipTally]:
    reads = [read_source(base, base.joinpath(name), PurePosixPath(name)) for name in sorted(names)]
    files = tuple(read for read in reads if isinstance(read, SourceFile))
    kinds = tuple(read for read in reads if isinstance(read, str) and read != 'not_a_file')
    return files, tally_skips((*kinds, *('unreadable',) * unreadable))


def walk(root: Path) -> Walk:
    if not root.exists():
        raise PathMissingError(path=root)
    resolved = root.resolve()
    names, unreadable, git_failed = list_names(resolved)
    base = resolved.parent if resolved.is_file() else resolved
    files, skipped = split_reads(base, names, unreadable)
    return Walk(files=files, skipped=skipped, git_failed=git_failed, single_file=resolved.is_file())


@dataclass(slots=True, kw_only=True, frozen=True)
class DiskTree:
    def walk(self, root: Path) -> Walk:
        return walk(root)

    def read(self, root: Path, name: PurePosixPath) -> SourceFile | SkipKind:
        return read_source(root, root.joinpath(name), name)
