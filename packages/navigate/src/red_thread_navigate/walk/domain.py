"""What a walk returns: the readable source files under a root and a tally of what was left out."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import PurePosixPath

MAX_FILE_BYTES = 1024 * 1024
SNIFF_BYTES = 8 * 1024
SKIPPED_DIRECTORIES = frozenset({
    '.svn',
    '.mypy_cache',
    '.pytest_cache',
    '.ruff_cache',
    '.tox',
    '.venv',
    '__pycache__',
    'build',
    'dist',
    'node_modules',
    'site-packages',
    'target',
    'venv',
})

type SkipKind = Literal['too_large', 'binary', 'not_utf8', 'outside_root', 'unreadable']


@dataclass(slots=True, kw_only=True, frozen=True)
class SourceFile:
    path: PurePosixPath
    text: str


@dataclass(slots=True, kw_only=True, frozen=True)
class SkipTally:
    too_large: int = 0
    binary: int = 0
    not_utf8: int = 0
    outside_root: int = 0
    unreadable: int = 0

    @property
    def total(self) -> int:
        return self.too_large + self.binary + self.not_utf8 + self.outside_root + self.unreadable

    @property
    def parts(self) -> tuple[str, ...]:
        counted = (
            (self.too_large, 'over 1 MiB'),
            (self.binary, 'binary'),
            (self.not_utf8, 'not UTF-8'),
            (self.outside_root, 'outside the root'),
            (self.unreadable, 'unreadable'),
        )
        return tuple(f'{count} {label}' for count, label in counted if count)


@dataclass(slots=True, kw_only=True, frozen=True)
class Walk:
    files: tuple[SourceFile, ...]
    skipped: SkipTally
    git_failed: bool = False

    @property
    def note(self) -> str | None:
        parts = []
        if self.skipped.total:
            parts.append(f'skipped {", ".join(self.skipped.parts)}')
        if self.git_failed:
            parts.append('git listing failed, walked the directory instead')
        return '; '.join(parts) or None


@dataclass(slots=True, kw_only=True, frozen=True)
class TrackedFiles:
    names: tuple[str, ...] | None
    failed: bool = False


def tally_skips(kinds: tuple[SkipKind, ...]) -> SkipTally:
    return SkipTally(
        too_large=kinds.count('too_large'),
        binary=kinds.count('binary'),
        not_utf8=kinds.count('not_utf8'),
        outside_root=kinds.count('outside_root'),
        unreadable=kinds.count('unreadable'),
    )
