"""Lens outputs: a selection picks and ranks live findings, and the ledger supplies their words."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from red_thread_core.documents import Document, Paragraph, PointList, Section, parse_line
from red_thread_core.dto import DTO
from red_thread_core.util import squeeze

from red_thread_casefile.documents import FindingNodeBuilder, list_findings_block
from red_thread_casefile.domain import (
    CASE_FILE,
    PROGRAM,
    STATE_DIRECTORY,
    THREAD_HOME,
    FindingKind,
    shorten_head,
)
from red_thread_casefile.errors import LensOverBudgetError, UnknownSelectedFindingError
from red_thread_casefile.views import Annotator, CheckReport

if TYPE_CHECKING:
    from red_thread_casefile.documents import FindingNode, Note, Wording
    from red_thread_casefile.domain import Case, CaseFinding, CaseLedger
    from red_thread_casefile.policy import CitationCheck

type LensName = Literal['brief', 'issue', 'handoff', 'report']
type FixedPart = Literal['goal', 'pointers', 'reading']

LENS_NAMES: tuple[LensName, ...] = ('brief', 'issue', 'handoff', 'report')


class Part(DTO, frozen=True, kw_only=True, forbid_unknown_fields=True, gc=False):
    title: str
    kind: FindingKind | None = None
    fixed: FixedPart | None = None


class Lens(DTO, frozen=True, kw_only=True, forbid_unknown_fields=True, gc=False):
    name: LensName
    intro: str
    budget: int
    parts: tuple[Part, ...]


class LensBook(DTO, frozen=True, kw_only=True, forbid_unknown_fields=True, gc=False):
    reading: tuple[str, ...]
    lenses: tuple[Lens, ...]

    def get(self, name: LensName) -> Lens:
        return next(lens for lens in self.lenses if lens.name == name)


def count_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


class Selection(DTO, frozen=True, kw_only=True, gc=False):
    title: str | None = None
    goal: str | None = None
    include: tuple[str, ...] | None = None
    blocking: tuple[str, ...] | None = None

    @property
    def named(self) -> tuple[str, ...]:
        return (*(self.include or ()), *(self.blocking or ()))

    def is_blocking(self, finding: CaseFinding) -> bool:
        return finding.finding_id in (self.blocking or ())

    def admits(self, finding: CaseFinding) -> bool:
        if self.include is None or finding.kind == 'decision':
            return True
        return finding.finding_id in self.include or self.is_blocking(finding)

    def rank(self, finding: CaseFinding) -> tuple[bool, int]:
        chosen = self.include or ()
        position = chosen.index(finding.finding_id) if finding.finding_id in chosen else len(chosen)
        return (not self.is_blocking(finding), position)


@dataclass(slots=True, kw_only=True, frozen=True)
class Edition:
    case: Case
    ledger: CaseLedger
    head: str | None = None
    citation_checks: tuple[CitationCheck, ...] = ()

    @property
    def short_head(self) -> str:
        return shorten_head(self.head)

    @property
    def annotator(self) -> Annotator:
        return Annotator(head=self.head, citation_checks=self.citation_checks)


@dataclass(slots=True, kw_only=True, frozen=True)
class Composer:
    lens: Lens
    selection: Selection
    edition: Edition
    wording: Wording
    reading: tuple[str, ...]

    def get_selection_problem(self) -> UnknownSelectedFindingError | None:
        live = {finding.finding_id for finding in self.edition.ledger.live}
        unknown = next(
            (finding_id for finding_id in self.selection.named if finding_id not in live), None
        )
        if unknown is None:
            return None
        return UnknownSelectedFindingError(finding_id=unknown)

    def get_budget_problem(self, text: str) -> LensOverBudgetError | None:
        lines = count_lines(text)
        if lines <= self.lens.budget:
            return None
        return LensOverBudgetError(lens=self.lens.name, lines=lines, budget=self.lens.budget)

    def select(self, kind: FindingKind) -> tuple[CaseFinding, ...]:
        admitted = filter(self.selection.admits, self.edition.ledger.select(kind))
        return tuple(sorted(admitted, key=self.selection.rank))

    def list_notes(self, finding: CaseFinding) -> tuple[Note, ...]:
        notes = self.wording.list_caveat_notes(finding)
        if self.selection.blocking is None or finding.kind != 'open':
            return notes
        urgency = 'blocking' if self.selection.is_blocking(finding) else 'not blocking'
        return (self.wording.write_note('urgency', urgency), *notes)

    def create_finding(self, finding: CaseFinding) -> FindingNode:
        builder = FindingNodeBuilder(annotator=self.edition.annotator)
        return builder.build(finding, self.list_notes(finding))

    def list_pointers(self) -> PointList:
        case = self.edition.case
        location = f'{STATE_DIRECTORY}/{case.id}'
        checked = CheckReport(citation_checks=self.edition.citation_checks).summary
        threads = f'with one file per thread under `{THREAD_HOME}/`'
        pointers = [
            f'Case file: `{location}/{CASE_FILE}`, {threads}.',
            f'Citations checked at commit {self.edition.short_head}: {checked}.',
            f'Check again with the red-thread plugin: `{PROGRAM} check --case {location}`',
        ]
        if case.page_url is not None:
            pointers.append(f'Board: {case.page_url}')
        return PointList(points=tuple(map(parse_line, pointers)))

    def write_goal(self) -> Paragraph:
        case = self.edition.case
        if self.selection.goal is not None:
            return Paragraph(line=parse_line(squeeze(self.selection.goal)))
        return Paragraph(line=parse_line(f'{case.target} The bar for an answer: {case.bar}'))

    def compose_part(self, part: Part) -> Section:
        if part.kind:
            findings = tuple(map(self.create_finding, self.select(part.kind)))
            blocks = list_findings_block(findings)
            note = self.wording.describe_kind(part.kind)
            return Section(title=part.title, blocks=blocks, kind=part.kind, note=note)

        if part.fixed == 'goal':
            return Section(title=part.title, blocks=(self.write_goal(),))

        if part.fixed == 'reading':
            reading = PointList(points=tuple(map(parse_line, self.reading)))
            return Section(title=part.title, blocks=(reading,))

        return Section(title=part.title, blocks=(self.list_pointers(),))

    def compose(self) -> Document:
        case = self.edition.case
        ledger = self.edition.ledger
        sections = map(self.compose_part, self.lens.parts)
        summary = (
            f'{self.lens.intro} case `{case.id}` ({case.kind}), round {ledger.last_round}, '
            f'at commit {self.edition.short_head}.'
        )
        return Document(
            title=squeeze(self.selection.title or case.target),
            summary=(parse_line(summary),),
            sections=tuple(section for section in sections if section.blocks),
        )
