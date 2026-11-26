"""The edge: builds a planner over one plan.md, the cases beside it, git and the clock."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from red_thread_core.store import GitSourceTree, SystemClock

from red_thread_plans.services import Planner
from red_thread_plans.store import DirectoryCaseShelf, FilePlanRepository

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_core.store import Clock

STATE_DEPTH = 2
ROOT_DEPTH = 3


@dataclass(slots=True, kw_only=True, frozen=True)
class Plans:
    clock: Clock = field(default_factory=SystemClock)

    def open_planner(self, path: Path) -> Planner:
        resolved = path.resolve()
        return Planner(
            shelf=DirectoryCaseShelf(state=resolved.parents[STATE_DEPTH]),
            plan=FilePlanRepository(path=resolved),
            tree=GitSourceTree(root=resolved.parents[ROOT_DEPTH]),
            clock=self.clock,
        )
