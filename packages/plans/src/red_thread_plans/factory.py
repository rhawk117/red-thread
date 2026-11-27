"""The edge: builds a planner over one plan.md, the cases beside it, git and the clock."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from red_thread_core.codec import create_yaml_codec
from red_thread_core.store import GitSourceTree, SystemClock

from red_thread_plans.packaged import load_outline
from red_thread_plans.services import Planner
from red_thread_plans.store import DirectoryCaseShelf, FilePlanRepository

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_core.codec import Codec
    from red_thread_core.store import Clock

    from red_thread_plans.domain import Outline

STATE_DEPTH = 2
ROOT_DEPTH = 3


@dataclass(slots=True, kw_only=True, frozen=True)
class Plans:
    clock: Clock = field(default_factory=SystemClock)
    outline: Outline = field(default_factory=load_outline)
    codec: Codec = field(default_factory=create_yaml_codec)

    def open_planner(self, path: Path) -> Planner:
        resolved = path.resolve()
        return Planner(
            shelf=DirectoryCaseShelf(state=resolved.parents[STATE_DEPTH], codec=self.codec),
            plan=FilePlanRepository(path=resolved),
            tree=GitSourceTree(root=resolved.parents[ROOT_DEPTH]),
            clock=self.clock,
            outline=self.outline,
            codec=self.codec,
        )
