"""The edge: builds a case file over a real directory, its git tree and the system clock."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from red_thread_casefile.plans.store import DirectoryPlanRepository
from red_thread_casefile.services import CaseFile, Planner, Press
from red_thread_casefile.store import (
    DirectoryCaseRepository,
    DirectoryPageStore,
    GitSourceTree,
    SystemClock,
)

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_casefile.store import Clock

ROOT_DEPTH = 1


@dataclass(slots=True, kw_only=True, frozen=True)
class CaseFiles:
    clock: Clock = field(default_factory=SystemClock)

    def bind(self, directory: Path) -> CaseFile:
        resolved = directory.resolve()
        return CaseFile(
            repository=DirectoryCaseRepository(directory=resolved),
            tree=GitSourceTree(root=resolved.parents[ROOT_DEPTH]),
            clock=self.clock,
        )

    def open_press(self, directory: Path) -> Press:
        resolved = directory.resolve()
        return Press(record=self.bind(resolved), pages=DirectoryPageStore(directory=resolved))

    def open_planner(self, directory: Path) -> Planner:
        resolved = directory.resolve()
        return Planner(
            record=self.bind(resolved),
            plans=DirectoryPlanRepository(directory=resolved),
            pages=DirectoryPageStore(directory=resolved),
        )
