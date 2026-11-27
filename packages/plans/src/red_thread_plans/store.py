"""Where a plan lives: one plan.md per ticket, and the cases beside it that it reads."""

from dataclasses import dataclass
from pathlib import PurePath
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from red_thread_casefile.errors import MalformedCaseError
from red_thread_casefile.schemas import load_record, read_case_file
from red_thread_casefile.store import DirectoryCaseRepository
from red_thread_core.store import create_exclusive

from red_thread_plans.domain import TICKET_HOME
from red_thread_plans.errors import MissingPlanError, PlanExistsError

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_casefile.domain import CaseRecord

NOT_CASES = frozenset({'.', '..', TICKET_HOME, 'plans'})


@runtime_checkable
class PlanRepository(Protocol):
    def exists(self) -> bool: ...

    def read(self) -> str: ...

    def create(self, text: str) -> Path: ...


@runtime_checkable
class CaseShelf(Protocol):
    def find(self, case_id: str) -> CaseRecord | None: ...


@dataclass(slots=True, kw_only=True, frozen=True)
class FilePlanRepository:
    path: Path

    def exists(self) -> bool:
        return self.path.is_file()

    def read(self) -> str:
        if not self.exists():
            raise MissingPlanError(path=self.path)
        return self.path.read_text(encoding='utf-8')

    def create(self, text: str) -> Path:
        if (error := create_exclusive(self.path, text)) is not None:
            raise PlanExistsError(path=self.path) from error
        return self.path


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

        record = load_record(read_case_file(repository.read()))
        if isinstance(record, MalformedCaseError):
            raise record

        return record
