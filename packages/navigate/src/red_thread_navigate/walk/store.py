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
    TrackedFiles,
    Walk,
    tally_skips,
)

if TYPE_CHECKING:
    from red_thread_navigate.walk.domain import SkipKind


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
    return TrackedFiles(names=tuple(name for name in names if name))


def is_inside(root: Path, path: Path) -> bool:
    return path.resolve().is_relative_to(root)


def keeps_directory(name: str) -> bool:
    return not name.startswith('.') and name not in SKIPPED_DIRECTORIES


def list_directory(root: Path) -> tuple[tuple[str, ...], int, int]:
    names: list[str] = []
    escaped = 0
    errors: list[OSError] = []
    for current, directories, files in os.walk(root, followlinks=False, onerror=errors.append):
        base = Path(current)
        linked = [name for name in directories if base.joinpath(name).is_symlink()]
        escaped += sum(not is_inside(root, base.joinpath(name)) for name in linked)
        directories[:] = [
            name for name in directories if name not in linked and keeps_directory(name)
        ]
        names.extend(base.joinpath(name).relative_to(root).as_posix() for name in files)
    return tuple(names), escaped, len(errors)


def read_limited(target: Path) -> bytes | SkipKind:
    try:
        if not target.is_file():
            return 'not_a_file'
        if target.stat().st_size > MAX_FILE_BYTES:
            return 'too_large'
        return target.read_bytes()
    except OSError:
        return 'unreadable'


def read_source(root: Path, path: Path, name: PurePosixPath) -> SourceFile | SkipKind:
    target = path.resolve()
    if not target.is_relative_to(root):
        return 'outside_root'
    data = read_limited(target)
    if isinstance(data, str):
        return data
    if b'\0' in data[:SNIFF_BYTES]:
        return 'binary'
    try:
        return SourceFile(path=name, text=data.decode('utf-8'))
    except UnicodeDecodeError:
        return 'not_utf8'


def walk(root: Path) -> Walk:
    base = root.resolve()
    escaped = unreadable = 0
    git_failed = False
    if base.is_file():
        names = (base.name,)
        base = base.parent
    else:
        tracked = list_tracked(base)
        git_failed = tracked.failed
        if tracked.names is None:
            names, escaped, unreadable = list_directory(base)
        else:
            names = tracked.names
    reads = [read_source(base, base.joinpath(name), PurePosixPath(name)) for name in sorted(names)]
    files = tuple(read for read in reads if isinstance(read, SourceFile))
    kinds = tuple(read for read in reads if isinstance(read, str) and read != 'not_a_file')
    skipped = tally_skips((*kinds, *('outside_root',) * escaped, *('unreadable',) * unreadable))
    return Walk(files=files, skipped=skipped, git_failed=git_failed)
