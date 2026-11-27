"""The board, the documents and the check report: rendered from the ledger, never from memory."""

import sys
from dataclasses import dataclass, field
from itertools import chain
from typing import TYPE_CHECKING, Self

from red_thread_core.dto import DTO
from red_thread_core.util import squeeze

from red_thread_casefile.domain import FindingKind, is_current, shorten_head
from red_thread_casefile.policy import CITE_STATES, FAILING_STATES, QUIET_STATES, tally_states

if TYPE_CHECKING:
    from red_thread_casefile.domain import Case, CaseFinding, CaseLedger, Verdict
    from red_thread_casefile.errors import CaseFileError
    from red_thread_casefile.policy import CitationCheck

NO_COMMIT = 'no commit'
LEAD_FLAG_PREFIX = 'lead, '
CITE_FLAG_PREFIX = 'citation '
FAULT_ADVICE = (
    'Correct a finding where it stands until a gate or a report has shown it. After that, '
    'append a finding whose supersedes names it instead.'
)


class Heading(DTO, frozen=True, kw_only=True, forbid_unknown_fields=True, gc=False):
    kind: FindingKind
    title: str
    note: str


def list_caveats(finding: CaseFinding) -> list[str]:
    labelled = (('rests on', finding.rests_on), ('refuted by', finding.refuted_if))
    return [f'{label}: {value}' for label, value in labelled if value is not None]


def describe_lead(recorded: str) -> str:
    return f'{LEAD_FLAG_PREFIX}recorded at {recorded}'


def get_shown_verdict(finding: CaseFinding) -> Verdict | None:
    return finding.verdict if finding.kind != 'known' else None


def label_finding(finding: CaseFinding) -> str:
    shown = get_shown_verdict(finding)
    verdict = f'{shown}: ' if shown else ''
    return f'{verdict}{squeeze(finding.text)}'


def list_citation_flags(citation_check: CitationCheck | None) -> list[str]:
    if not citation_check:
        return []
    failing = (
        [f'{CITE_FLAG_PREFIX}{citation_check.state}']
        if citation_check.state in FAILING_STATES
        else []
    )
    moved_to = citation_check.moved_to
    moved = [f'{CITE_FLAG_PREFIX}moved to line {moved_to}'] if moved_to is not None else []
    return [*failing, *moved]


@dataclass(slots=True, kw_only=True, frozen=True)
class Annotator:
    head: str | None = None
    citation_checks: tuple[CitationCheck, ...] = ()

    def find(self, finding: CaseFinding) -> CitationCheck | None:
        return next(
            (
                citation_check
                for citation_check in self.citation_checks
                if citation_check.finding_id == finding.finding_id
            ),
            None,
        )

    def get_recorded_head(self, finding: CaseFinding) -> str | None:
        if is_current(finding.head, self.head):
            return None
        return shorten_head(finding.head, NO_COMMIT)

    def list_lead_flags(self, finding: CaseFinding) -> list[str]:
        recorded = self.get_recorded_head(finding)
        if recorded is None:
            return []
        return [describe_lead(recorded)]

    def list_flags(self, finding: CaseFinding) -> list[str]:
        return [*self.list_lead_flags(finding), *list_citation_flags(self.find(finding))]


class BoardOptions(DTO, frozen=True, kw_only=True, gc=False):
    per_section: int = 6

    @classmethod
    def full(cls) -> Self:
        return cls(per_section=sys.maxsize)


@dataclass(slots=True, kw_only=True, frozen=True)
class Board:
    case: Case
    ledger: CaseLedger
    headings: tuple[Heading, ...]
    head: str | None = None
    options: BoardOptions = field(default_factory=BoardOptions)
    citation_checks: tuple[CitationCheck, ...] = ()

    @property
    def annotator(self) -> Annotator:
        return Annotator(head=self.head, citation_checks=self.citation_checks)

    def list_remarks(self, finding: CaseFinding) -> list[str]:
        retired = ', '.join(finding.supersedes)
        retires = [f'retires: {retired}'] if retired else []
        return [*list_caveats(finding), *retires]

    def list_notes(self, finding: CaseFinding) -> list[str]:
        citation = [f'`{finding.citation}`'] if finding.citation is not None else []
        flags = self.annotator.list_flags(finding)
        return [*self.list_remarks(finding), *citation, finding.source, *flags]

    def describe(self, finding: CaseFinding) -> str:
        notes = '; '.join(self.list_notes(finding))
        return f'- [{finding.finding_id}] {label_finding(finding)} ({notes})'

    def render_section(self, heading: Heading) -> list[str]:
        findings = self.ledger.select(heading.kind)
        if not findings:
            return []
        shown = findings[-self.options.per_section :]
        hidden = len(findings) - len(shown)
        lines = ['', f'## {heading.title} ({len(findings)})']
        if hidden:
            lines.append(f'(+{hidden} earlier, shown by render --full)')
        lines.extend(map(self.describe, shown))
        return lines

    def render_header(self) -> list[str]:
        live = len(self.ledger.live)
        retired = len(self.ledger.findings) - live
        head = shorten_head(self.head)
        lines = [
            f'# {self.case.id}',
            f'Target: {self.case.target}',
            f'Bar: {self.case.bar}',
            f'Kind: {self.case.kind} | Round: {self.ledger.last_round} | HEAD: {head}',
            f'Findings: {live} live, {retired} retired',
        ]
        if listed := self.ledger.describe_threads():
            lines.append(f'Threads: {listed}')
        if self.case.page_url is not None:
            lines.append(f'Page: {self.case.page_url}')
        return lines

    def render(self) -> str:
        sections = map(self.render_section, self.headings)
        return '\n'.join((*self.render_header(), *chain.from_iterable(sections)))


@dataclass(slots=True, kw_only=True, frozen=True)
class CheckReport:
    citation_checks: tuple[CitationCheck, ...]
    problems: tuple[CaseFileError, ...] = ()

    @property
    def has_failures(self) -> bool:
        drifted = any(
            citation_check.state in FAILING_STATES for citation_check in self.citation_checks
        )
        return drifted or bool(self.problems)

    def render_problems(self) -> list[str]:
        if not self.problems:
            return []
        return [
            f'{len(self.problems)} faults; check changed no file:',
            *(f'- {problem}' for problem in self.problems),
            FAULT_ADVICE,
            '',
        ]

    @property
    def summary(self) -> str:
        counted = tally_states(self.citation_checks)
        return ', '.join(f'{counted[state]} {state}' for state in CITE_STATES)

    def describe(self, citation_check: CitationCheck) -> str:
        moved = (
            f', now at line {citation_check.moved_to}'
            if citation_check.moved_to is not None
            else ''
        )
        check = citation_check
        return f'- [{check.finding_id}] {check.state}: `{check.citation}`{moved}'

    def render(self) -> str:
        flagged = (
            citation_check
            for citation_check in self.citation_checks
            if citation_check.state not in QUIET_STATES
        )
        lines = [
            *self.render_problems(),
            f'checked {len(self.citation_checks)} citations: {self.summary}',
            *map(self.describe, flagged),
        ]
        if any(citation_check.state in FAILING_STATES for citation_check in self.citation_checks):
            lines.append(
                'A changed or missing citation is no longer evidence. Verify the claim again, '
                'then retire the old finding with supersedes.'
            )
        return '\n'.join(lines)
