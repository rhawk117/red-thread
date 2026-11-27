"""The planner: starts a ticket's plan beside its cases, and checks a plan against them."""

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from red_thread_casefile.domain import date_of, shorten_head
from red_thread_casefile.services.casefile import EXCLUDED
from red_thread_core.dto import DTO

from red_thread_plans.domain import Frontmatter, find_refs
from red_thread_plans.errors import (
    NoCasesError,
    PlanRejectedError,
    PlanShapeError,
    UnknownCaseError,
)
from red_thread_plans.policy import PlanPolicy, create_grounds
from red_thread_plans.schemas import read_plan, write_plan

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from red_thread_casefile.domain import CaseRecord
    from red_thread_core.codec import Codec
    from red_thread_core.store import Clock, SourceTree

    from red_thread_plans.domain import Opening, Outline, PlanDocument
    from red_thread_plans.store import CaseShelf, PlanRepository


class Checked(DTO, frozen=True, kw_only=True, gc=False):
    criteria: int
    entries: int


def alias_cases(case_ids: tuple[str, ...]) -> dict[str, str]:
    return {f'C{number}': case_id for number, case_id in enumerate(case_ids, 1)}


def count_entries(document: PlanDocument) -> int:
    return len({ref for line in document.criteria for ref in find_refs(line)})


@dataclass(slots=True, kw_only=True, frozen=True)
class Planner:
    shelf: CaseShelf
    plan: PlanRepository
    tree: SourceTree
    clock: Clock
    outline: Outline
    codec: Codec

    def gather(self, cases: Mapping[str, str]) -> dict[str, CaseRecord]:
        found = ((alias, self.shelf.find(case_id)) for alias, case_id in cases.items())
        return {alias: record for alias, record in found if record is not None}

    def stamp(self, opening: Opening) -> Frontmatter:
        head = self.tree.get_head()
        return Frontmatter(
            id=opening.id,
            title=opening.title,
            created=date.fromisoformat(date_of(self.clock.now())),
            head=None if head is None else shorten_head(head),
            cases=alias_cases(opening.case_ids),
        )

    def find_missing(self, case_ids: tuple[str, ...]) -> str | None:
        return next((case_id for case_id in case_ids if self.shelf.find(case_id) is None), None)

    def open(self, opening: Opening) -> Path:
        if not opening.case_ids:
            raise NoCasesError

        missing = self.find_missing(opening.case_ids)
        if missing is not None:
            raise UnknownCaseError(alias=None, case_id=missing)

        self.tree.exclude(EXCLUDED)
        return self.plan.create(write_plan(self.codec, self.stamp(opening), self.outline))

    def check(self) -> Checked:
        document = read_plan(self.codec, self.plan.read())
        if isinstance(document, PlanShapeError):
            raise document

        cases = document.frontmatter.cases
        records = self.gather(cases)
        ledgers = {alias: record.ledger for alias, record in records.items()}
        missing = {alias: case_id for alias, case_id in cases.items() if alias not in records}
        policy = PlanPolicy(
            document=document,
            grounds=create_grounds(ledgers),
            outline=self.outline,
            missing=missing,
        )
        if problems := policy.get_plan_issues():
            raise PlanRejectedError(problems=problems)

        return Checked(criteria=len(document.criteria), entries=count_entries(document))
