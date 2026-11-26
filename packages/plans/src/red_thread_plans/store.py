"""Where a plan lives: its index and one JSON file per revision, and the cases it reads."""

import re
from dataclasses import dataclass
from pathlib import PurePath
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from red_thread_casefile.store import DirectoryCaseRepository
from red_thread_core.places import PLAN_HOME

from red_thread_plans.domain import CaseRecord
from red_thread_plans.errors import CorruptPlanError, MissingPlanError, RevisionExistsError
from red_thread_plans.schemas import index_from_text, plan_from_text, to_text

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_plans.domain import Plan, PlanIndex

INDEX_FILE = 'plan.json'
REVISION_FILE = re.compile(r'r(?P<revision>[1-9]\d*)\.json')
NOT_CASES = frozenset({'.', '..', PLAN_HOME})


@runtime_checkable
class PlanRepository(Protocol):
    def exists(self) -> bool: ...

    def read_index(self) -> PlanIndex: ...

    def write_index(self, index: PlanIndex) -> None: ...

    def read_plans(self) -> tuple[Plan, ...]: ...

    def add(self, plan: Plan) -> Path: ...


@runtime_checkable
class CaseShelf(Protocol):
    def find(self, case_id: str) -> CaseRecord | None: ...


@dataclass(slots=True, kw_only=True, frozen=True)
class DirectoryPlanRepository:
    directory: Path

    @property
    def index_path(self) -> Path:
        return self.directory.joinpath(INDEX_FILE)

    def exists(self) -> bool:
        return self.index_path.is_file()

    def read_index(self) -> PlanIndex:
        if not self.exists():
            raise MissingPlanError(path=self.directory)
        try:
            return index_from_text(self.index_path.read_text(encoding='utf-8'))
        except ValueError as error:
            raise CorruptPlanError(path=self.index_path, reason=str(error)) from error

    def write_index(self, index: PlanIndex) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(to_text(index), encoding='utf-8')

    def locate(self, revision: int) -> Path:
        return self.directory.joinpath(f'r{revision}.json')

    def list_revisions(self) -> tuple[int, ...]:
        named = (REVISION_FILE.fullmatch(path.name) for path in self.directory.glob('r*.json'))
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
        self.directory.mkdir(parents=True, exist_ok=True)
        try:
            with path.open('x', encoding='utf-8') as target:
                target.write(to_text(plan))
        except FileExistsError as error:
            raise RevisionExistsError(path=path) from error
        return path


def is_case_name(case_id: str) -> bool:
    return PurePath(case_id).name == case_id and case_id not in NOT_CASES


@dataclass(slots=True, kw_only=True, frozen=True)
class DirectoryCaseShelf:
    state: Path

    def find(self, case_id: str) -> CaseRecord | None:
        if not is_case_name(case_id):
            return None

        repository = DirectoryCaseRepository(directory=self.state.joinpath(case_id))
        if not repository.exists():
            return None

        return CaseRecord(case=repository.read_case(), ledger=repository.read_ledger())
