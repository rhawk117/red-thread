"""A plan and the cases it reads, held in memory and refusing what the directories refuse."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from red_thread_plans.errors import MissingPlanError, RevisionExistsError

if TYPE_CHECKING:
    from red_thread_plans.domain import CaseRecord, Plan, PlanIndex

PLAN_DIRECTORY = Path('plan')


def locate_revision(revision: int) -> Path:
    return PLAN_DIRECTORY.joinpath(f'r{revision}.json')


@dataclass(slots=True, kw_only=True, frozen=True)
class MemoryPlanRepository:
    plans: list[Plan] = field(default_factory=list)
    indexes: list[PlanIndex] = field(default_factory=list)

    @property
    def revisions(self) -> tuple[int, ...]:
        return tuple(plan.revision for plan in self.plans)

    def exists(self) -> bool:
        return bool(self.indexes)

    def read_index(self) -> PlanIndex:
        if not self.indexes:
            raise MissingPlanError(path=PLAN_DIRECTORY)
        return self.indexes[-1]

    def write_index(self, index: PlanIndex) -> None:
        self.indexes.append(index)

    def read_plans(self) -> tuple[Plan, ...]:
        return tuple(self.plans)

    def add(self, plan: Plan) -> Path:
        path = locate_revision(plan.revision)
        if plan.revision in self.revisions:
            raise RevisionExistsError(path=path)
        self.plans.append(plan)
        return path


@dataclass(slots=True, kw_only=True, frozen=True)
class MemoryCaseShelf:
    records: dict[str, CaseRecord] = field(default_factory=dict)

    def find(self, case_id: str) -> CaseRecord | None:
        return self.records.get(case_id)
