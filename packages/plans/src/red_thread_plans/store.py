"""Where a case keeps its plan revisions: one JSON file each, written once and never replaced."""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from red_thread_plans.errors import CorruptPlanError, RevisionExistsError
from red_thread_plans.schemas import plan_from_text, plan_to_text

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_plans.domain import Plan

PLAN_DIRECTORY = 'plans'
REVISION_FILE = re.compile(r'r(?P<revision>[1-9]\d*)\.json')


@runtime_checkable
class PlanRepository(Protocol):
    def read_plans(self) -> tuple[Plan, ...]: ...

    def add(self, plan: Plan) -> Path: ...


@dataclass(slots=True, kw_only=True, frozen=True)
class DirectoryPlanRepository:
    directory: Path

    @property
    def folder(self) -> Path:
        return self.directory.joinpath(PLAN_DIRECTORY)

    def locate(self, revision: int) -> Path:
        return self.folder.joinpath(f'r{revision}.json')

    def list_revisions(self) -> tuple[int, ...]:
        named = (REVISION_FILE.fullmatch(path.name) for path in self.folder.glob('r*.json'))
        return tuple(sorted(int(found['revision']) for found in named if found))

    def read(self, revision: int) -> Plan:
        path = self.locate(revision)
        try:
            return plan_from_text(path.read_text(encoding='utf-8'))
        except ValueError as error:
            raise CorruptPlanError(path=path, reason=str(error)) from error

    def read_plans(self) -> tuple[Plan, ...]:
        return tuple(map(self.read, self.list_revisions()))

    def add(self, plan: Plan) -> Path:
        path = self.locate(plan.revision)
        self.folder.mkdir(parents=True, exist_ok=True)
        try:
            with path.open('x', encoding='utf-8') as target:
                target.write(plan_to_text(plan))
        except FileExistsError as error:
            raise RevisionExistsError(path=path) from error
        return path
