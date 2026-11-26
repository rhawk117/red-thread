"""Plan revisions held in a list, refusing a revision already there as the directory does."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from red_thread_plans.errors import RevisionExistsError

if TYPE_CHECKING:
    from red_thread_plans.domain import Plan


def locate_revision(revision: int) -> Path:
    return Path('plans', f'r{revision}.json')


@dataclass(slots=True, kw_only=True, frozen=True)
class MemoryPlanRepository:
    plans: list[Plan] = field(default_factory=list)

    @property
    def revisions(self) -> tuple[int, ...]:
        return tuple(plan.revision for plan in self.plans)

    def read_plans(self) -> tuple[Plan, ...]:
        return tuple(self.plans)

    def add(self, plan: Plan) -> Path:
        path = locate_revision(plan.revision)
        if plan.revision in self.revisions:
            raise RevisionExistsError(path=path)
        self.plans.append(plan)
        return path
