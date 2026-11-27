"""What makes a plan sound: its sections written, and every criterion resting on live findings."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from red_thread_plans.domain import ACCEPTANCE, RESTING_KINDS, SETTLED, find_cited_finding_ids
from red_thread_plans.errors import (
    EmptySectionError,
    GroundlessCriterionError,
    MissingSectionError,
    NoCasesError,
    NoCriteriaError,
    PlanError,
    RetiredFindingError,
    UnknownCaseError,
    UnknownFindingError,
    UnsetLightsError,
    WrongFindingKindError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from red_thread_casefile.domain import CaseFinding, CaseLedger
    from red_thread_core.lines import Line

    from red_thread_plans.domain import Outline, PlanDocument

type Problems = tuple[PlanError, ...]


@dataclass(slots=True, kw_only=True, frozen=True)
class Grounds:
    live: Mapping[str, CaseFinding] = field(default_factory=dict)
    known: frozenset[str] = frozenset()

    def get_finding_id_problem(self, line: int, finding_id: str) -> PlanError | None:
        if finding_id not in self.known:
            return UnknownFindingError(line=line, finding_id=finding_id)

        if finding_id not in self.live:
            return RetiredFindingError(line=line, finding_id=finding_id)

        return None

    def get_resting_problem(self, line: int, finding_id: str) -> PlanError | None:
        if problem := self.get_finding_id_problem(line, finding_id):
            return problem

        kind = self.live[finding_id].kind
        if kind not in RESTING_KINDS:
            return WrongFindingKindError(line=line, finding_id=finding_id, kind=kind)

        return None


def create_grounds(ledgers: Mapping[str, CaseLedger]) -> Grounds:
    cited = ledgers.items()
    live = {
        f'{alias}.{finding.finding_id}': finding
        for alias, ledger in cited
        for finding in ledger.live
    }
    known = frozenset(
        f'{alias}.{finding_id}' for alias, ledger in cited for finding_id in ledger.finding_ids
    )
    return Grounds(live=live, known=known)


def find_alias(finding_id: str) -> str:
    return finding_id.partition('.')[0]


@dataclass(slots=True, kw_only=True, frozen=True)
class PlanPolicy:
    document: PlanDocument
    grounds: Grounds
    outline: Outline
    missing: Mapping[str, str] = field(default_factory=dict)

    @property
    def is_settled(self) -> bool:
        return self.document.frontmatter.status in SETTLED

    def get_frontmatter_issues(self) -> Problems:
        frontmatter = self.document.frontmatter
        if not frontmatter.cases:
            return (NoCasesError(),)

        unknown = tuple(
            UnknownCaseError(alias=alias, case_id=case_id)
            for alias, case_id in self.missing.items()
        )
        unset = (
            (UnsetLightsError(status=frontmatter.status),)
            if self.is_settled and frontmatter.lights is None
            else ()
        )
        return (*unknown, *unset)

    def get_section_problem(self, title: str) -> PlanError | None:
        section = self.document.find_section(title)
        if section is None:
            return MissingSectionError(title=title)

        if title in self.outline.required and section.is_empty:
            return EmptySectionError(title=title, line=section.number)

        if title == ACCEPTANCE and not section.items:
            return NoCriteriaError(line=section.number)

        return None

    def get_section_issues(self) -> Problems:
        return tuple(filter(None, map(self.get_section_problem, self.outline.sections)))

    def is_checkable(self, finding_id: str) -> bool:
        return find_alias(finding_id) not in self.missing

    def get_line_issues(self, line: Line) -> Problems:
        finding_ids = filter(self.is_checkable, find_cited_finding_ids(line))
        found = (
            self.grounds.get_finding_id_problem(line.number, finding_id)
            for finding_id in finding_ids
        )
        return tuple(filter(None, found))

    def get_criterion_issues(self, line: Line) -> Problems:
        if not find_cited_finding_ids(line):
            return (GroundlessCriterionError(line=line.number),)

        finding_ids = filter(self.is_checkable, find_cited_finding_ids(line))
        found = (
            self.grounds.get_resting_problem(line.number, finding_id) for finding_id in finding_ids
        )
        return tuple(filter(None, found))

    def get_finding_id_issues(self) -> Problems:
        criteria = self.document.criteria
        others = (line for line in self.document.lines if line not in criteria)
        checked = (*map(self.get_line_issues, others), *map(self.get_criterion_issues, criteria))
        return tuple(problem for problems in checked for problem in problems)

    def get_plan_issues(self) -> Problems:
        return (
            *self.get_frontmatter_issues(),
            *self.get_section_issues(),
            *self.get_finding_id_issues(),
        )
