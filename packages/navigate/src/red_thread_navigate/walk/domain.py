"""What a walk returns: the readable source files under a root and a tally of what was left out."""

from collections import Counter
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

from red_thread_core.dto import DTO

if TYPE_CHECKING:
    from pathlib import Path

BYTES_PER_MIB = 1024 * 1024
MAX_FILE_BYTES = BYTES_PER_MIB
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

type SkipKind = Literal[
    'too_large', 'binary', 'not_utf8', 'outside_root', 'unreadable', 'not_a_file'
]


class SkipLabel(DTO, frozen=True, kw_only=True, gc=False):
    note: str
    reason: str


SKIP_LABELS: dict[SkipKind, SkipLabel] = {
    'too_large': SkipLabel(
        note=f'over {MAX_FILE_BYTES // BYTES_PER_MIB} MiB',
        reason=f'it is over {MAX_FILE_BYTES // BYTES_PER_MIB} MiB',
    ),
    'binary': SkipLabel(note='binary', reason='it is binary'),
    'not_utf8': SkipLabel(note='not UTF-8', reason='it is not UTF-8'),
    'outside_root': SkipLabel(note='outside the root', reason='it resolves outside the root'),
    'unreadable': SkipLabel(note='unreadable', reason='it cannot be read'),
    'not_a_file': SkipLabel(note='not a file', reason='it is not a file'),
}


class SourceFile(DTO, frozen=True, kw_only=True, gc=False):
    path: PurePosixPath
    text: str


@dataclass(slots=True, kw_only=True, frozen=True)
class SkipTally:
    counts: Counter[SkipKind] = field(default_factory=Counter)

    @property
    def total(self) -> int:
        return self.counts.total()

    @property
    def parts(self) -> tuple[str, ...]:
        return tuple(
            f'{self.counts[kind]} {label.note}'
            for kind, label in SKIP_LABELS.items()
            if self.counts[kind]
        )


class Walk(DTO, frozen=True, kw_only=True, gc=False):
    files: tuple[SourceFile, ...]
    skipped: SkipTally
    git_failed: bool = False
    single_file: bool = False

    @property
    def note(self) -> str | None:
        parts = []
        if self.skipped.total:
            parts.append(f'skipped {", ".join(self.skipped.parts)}')
        if self.git_failed:
            parts.append('git listing failed, walked the directory instead')
        return '; '.join(parts) or None


@runtime_checkable
class SourceTree(Protocol):
    def walk(self, root: Path) -> Walk: ...

    def read(self, root: Path, name: PurePosixPath) -> SourceFile | SkipKind: ...


class TrackedFiles(DTO, frozen=True, kw_only=True, gc=False):
    names: tuple[str, ...] | None
    failed: bool = False


def tally_skips(kinds: tuple[SkipKind, ...]) -> SkipTally:
    return SkipTally(counts=Counter(kinds))
