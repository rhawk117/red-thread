"""The edge: builds a planner over a real case directory, its git tree and the system clock."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from red_thread_casefile.factory import CaseFiles
from red_thread_core.store import DirectoryPageStore

from red_thread_plans.services import Planner
from red_thread_plans.store import DirectoryPlanRepository

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(slots=True, kw_only=True, frozen=True)
class Plans:
    cases: CaseFiles = field(default_factory=CaseFiles)

    def open_planner(self, directory: Path) -> Planner:
        resolved = directory.resolve()
        return Planner(
            record=self.cases.bind(resolved),
            plans=DirectoryPlanRepository(directory=resolved),
            pages=DirectoryPageStore(directory=resolved),
        )
