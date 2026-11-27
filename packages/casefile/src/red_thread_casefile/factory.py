"""The edge: builds a case file over a real directory, its git tree and the system clock."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from red_thread_core.codec import create_json_codec, create_yaml_codec
from red_thread_core.store import DirectoryPageStore, GitSourceTree, SystemClock

from red_thread_casefile.packaged import load_lens_book, load_wording
from red_thread_casefile.services import CaseFile, Press
from red_thread_casefile.store import DirectoryCaseRepository

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_core.codec import Codec
    from red_thread_core.store import Clock

    from red_thread_casefile.documents import Wording
    from red_thread_casefile.lenses import LensBook

ROOT_DEPTH = 1


@dataclass(slots=True, kw_only=True, frozen=True)
class CaseFiles:
    clock: Clock = field(default_factory=SystemClock)
    wording: Wording = field(default_factory=load_wording)
    book: LensBook = field(default_factory=load_lens_book)
    yaml: Codec = field(default_factory=create_yaml_codec)
    json: Codec = field(default_factory=create_json_codec)

    def bind(self, directory: Path) -> CaseFile:
        resolved = directory.resolve()
        return CaseFile(
            repository=DirectoryCaseRepository(directory=resolved),
            tree=GitSourceTree(root=resolved.parents[ROOT_DEPTH]),
            clock=self.clock,
            wording=self.wording,
            codec=self.yaml,
        )

    def open_press(self, directory: Path) -> Press:
        resolved = directory.resolve()
        return Press(
            record=self.bind(resolved),
            pages=DirectoryPageStore(directory=resolved),
            book=self.book,
        )
