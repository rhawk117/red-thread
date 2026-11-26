"""The edge: builds a planner over a plan directory, the cases beside it, git and the clock."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from red_thread_core.store import DirectoryPageStore, GitSourceTree, SystemClock

from red_thread_plans.services import Planner
from red_thread_plans.store import DirectoryCaseShelf, DirectoryPlanRepository

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_core.store import Clock

STATE_DEPTH = 1
ROOT_DEPTH = 2


@dataclass(slots=True, kw_only=True, frozen=True)
class Plans:
    clock: Clock = field(default_factory=SystemClock)

    def open_planner(self, directory: Path) -> Planner:
        resolved = directory.resolve()
        return Planner(
            shelf=DirectoryCaseShelf(state=resolved.parents[STATE_DEPTH]),
            plans=DirectoryPlanRepository(directory=resolved),
            pages=DirectoryPageStore(directory=resolved),
            tree=GitSourceTree(root=resolved.parents[ROOT_DEPTH]),
            clock=self.clock,
        )
