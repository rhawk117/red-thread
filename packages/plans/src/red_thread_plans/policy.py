"""What makes a plan sound: its sections written, and every criterion resting on live entries."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from red_thread_plans.domain import ACCEPTANCE, RESTING_KINDS, SETTLED
from red_thread_plans.errors import (
    EmptySectionError,
    GroundlessCriterionError,
    MissingSectionError,
    NoCasesError,
    NoCriteriaError,
    RetiredRefError,
    UnfitRefError,
    UnknownCaseError,
    UnknownRefError,
    UnsetLightsError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from red_thread_casefile.domain import Entry, Ledger
    from red_thread_casefile.errors import CaseFileError

    from red_thread_plans.domain import BodyLine, Outline, PlanDocument

type Problems = tuple[CaseFileError, ...]


@dataclass(slots=True, kw_only=True, frozen=True)
class Grounds:
    live: Mapping[str, Entry] = field(default_factory=dict)
    known: frozenset[str] = frozenset()

    def get_ref_problem(self, line: int, ref: str) -> CaseFileError | None:
        if ref not in self.known:
            return UnknownRefError(line=line, ref=ref)

        if ref not in self.live:
            return RetiredRefError(line=line, ref=ref)

        return None

    def get_resting_problem(self, line: int, ref: str) -> CaseFileError | None:
        if problem := self.get_ref_problem(line, ref):
            return problem

        kind = self.live[ref].kind
        if kind not in RESTING_KINDS:
            return UnfitRefError(line=line, ref=ref, kind=kind)

        return None


def create_grounds(ledgers: Mapping[str, Ledger]) -> Grounds:
    cited = ledgers.items()
    live = {f'{alias}.{entry.ref}': entry for alias, ledger in cited for entry in ledger.live}
    known = frozenset(f'{alias}.{ref}' for alias, ledger in cited for ref in ledger.refs)
    return Grounds(live=live, known=known)


def find_alias(ref: str) -> str:
    return ref.partition('.')[0]


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

    def get_section_problem(self, title: str) -> CaseFileError | None:
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

    def is_checkable(self, ref: str) -> bool:
        return find_alias(ref) not in self.missing

    def get_line_issues(self, line: BodyLine) -> Problems:
        refs = filter(self.is_checkable, line.refs)
        found = (self.grounds.get_ref_problem(line.number, ref) for ref in refs)
        return tuple(filter(None, found))

    def get_criterion_issues(self, line: BodyLine) -> Problems:
        if not line.refs:
            return (GroundlessCriterionError(line=line.number),)

        refs = filter(self.is_checkable, line.refs)
        found = (self.grounds.get_resting_problem(line.number, ref) for ref in refs)
        return tuple(filter(None, found))

    def get_ref_issues(self) -> Problems:
        criteria = self.document.criteria
        others = (line for line in self.document.lines if line not in criteria)
        checked = (*map(self.get_line_issues, others), *map(self.get_criterion_issues, criteria))
        return tuple(problem for problems in checked for problem in problems)

    def get_plan_issues(self) -> Problems:
        return (
            *self.get_frontmatter_issues(),
            *self.get_section_issues(),
            *self.get_ref_issues(),
        )
