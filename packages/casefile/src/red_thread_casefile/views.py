"""The board, the documents and the check report: rendered from the ledger, never from memory."""

import sys
from dataclasses import dataclass, field
from itertools import chain
from typing import TYPE_CHECKING, Self

from red_thread_core.util import squeeze

from red_thread_casefile.domain import shorten_head
from red_thread_casefile.policy import CITE_STATES, FAILING_STATES, QUIET_STATES, tally_states

if TYPE_CHECKING:
    from red_thread_core.mentions import PlanMention

    from red_thread_casefile.domain import Case, Entry, EntryKind, Ledger, Verdict
    from red_thread_casefile.policy import Finding

NO_COMMIT = 'no commit'
LEAD_FLAG_PREFIX = 'lead, '
CITE_FLAG_PREFIX = 'citation '


@dataclass(slots=True, kw_only=True, frozen=True)
class Heading:
    kind: EntryKind
    title: str
    note: str


HEADINGS = (
    Heading(
        kind='decision',
        title='Decided',
        note='What the owner decided or wants taken as given.',
    ),
    Heading(
        kind='known',
        title='Known',
        note='Claims with a citation that was opened and checked.',
    ),
    Heading(
        kind='hypothesis',
        title='Hypotheses',
        note='Explanations still to test, each with what would refute it.',
    ),
    Heading(
        kind='open',
        title='Open',
        note='Questions and claims that are not established yet.',
    ),
    Heading(
        kind='ruled_out',
        title='Ruled out',
        note='Dead ends, each closed by a citation or by the owner.',
    ),
    Heading(
        kind='next',
        title='Next',
        note='Steps left for whoever picks the case up.',
    ),
    Heading(
        kind='resource',
        title='Resources',
        note='Sources and references the case points to.',
    ),
)


def describe_kind(kind: EntryKind) -> str:
    return next(heading.note for heading in HEADINGS if heading.kind == kind)


def list_caveats(entry: Entry) -> list[str]:
    labelled = (('rests on', entry.rests_on), ('refuted by', entry.refute))
    return [f'{label}: {value}' for label, value in labelled if value is not None]


def describe_lead(recorded: str) -> str:
    return f'{LEAD_FLAG_PREFIX}recorded at {recorded}'


def get_shown_verdict(entry: Entry) -> Verdict | None:
    return entry.verdict if entry.kind != 'known' else None


def label_entry(entry: Entry) -> str:
    shown = get_shown_verdict(entry)
    verdict = f'{shown}: ' if shown else ''
    return f'{verdict}{squeeze(entry.text)}'


def list_cite_flags(finding: Finding | None) -> list[str]:
    if not finding:
        return []
    failing = [f'{CITE_FLAG_PREFIX}{finding.state}'] if finding.state in FAILING_STATES else []
    moved_to = finding.moved_to
    moved = [f'{CITE_FLAG_PREFIX}moved to line {moved_to}'] if moved_to is not None else []
    return [*failing, *moved]


@dataclass(slots=True, kw_only=True, frozen=True)
class Annotator:
    head: str | None = None
    findings: tuple[Finding, ...] = ()

    def find(self, entry: Entry) -> Finding | None:
        return next((finding for finding in self.findings if finding.ref == entry.ref), None)

    def get_recorded_head(self, entry: Entry) -> str | None:
        if entry.head == self.head:
            return None
        return shorten_head(entry.head, NO_COMMIT)

    def list_lead_flags(self, entry: Entry) -> list[str]:
        recorded = self.get_recorded_head(entry)
        if recorded is None:
            return []
        return [describe_lead(recorded)]

    def list_flags(self, entry: Entry) -> list[str]:
        return [*self.list_lead_flags(entry), *list_cite_flags(self.find(entry))]


@dataclass(slots=True, kw_only=True, frozen=True)
class BoardOptions:
    per_section: int = 6

    @classmethod
    def full(cls) -> Self:
        return cls(per_section=sys.maxsize)


@dataclass(slots=True, kw_only=True, frozen=True)
class Board:
    case: Case
    ledger: Ledger
    head: str | None = None
    plans: tuple[PlanMention, ...] = ()
    options: BoardOptions = field(default_factory=BoardOptions)
    findings: tuple[Finding, ...] = ()

    @property
    def annotator(self) -> Annotator:
        return Annotator(head=self.head, findings=self.findings)

    def list_remarks(self, entry: Entry) -> list[str]:
        retired = ', '.join(entry.supersedes)
        retires = [f'retires: {retired}'] if retired else []
        return [*list_caveats(entry), *retires]

    def list_notes(self, entry: Entry) -> list[str]:
        cite = [f'`{entry.cite}`'] if entry.cite is not None else []
        flags = self.annotator.list_flags(entry)
        return [*self.list_remarks(entry), *cite, entry.source, *flags]

    def describe(self, entry: Entry) -> str:
        notes = '; '.join(self.list_notes(entry))
        return f'- [{entry.ref}] {label_entry(entry)} ({notes})'

    def render_section(self, heading: Heading) -> list[str]:
        entries = self.ledger.select(heading.kind)
        if not entries:
            return []
        shown = entries[-self.options.per_section :]
        hidden = len(entries) - len(shown)
        lines = ['', f'## {heading.title} ({len(entries)})']
        if hidden:
            lines.append(f'(+{hidden} earlier, shown by render --full)')
        lines.extend(map(self.describe, shown))
        return lines

    def render_header(self) -> list[str]:
        live = len(self.ledger.live)
        retired = len(self.ledger.entries) - live
        head = shorten_head(self.head)
        lines = [
            f'# {self.case.id}',
            f'Target: {self.case.target}',
            f'Bar: {self.case.bar}',
            f'Kind: {self.case.kind} | Round: {self.ledger.last_round} | HEAD: {head}',
            f'Entries: {live} live, {retired} retired',
        ]
        if listed := self.ledger.describe_threads():
            lines.append(f'Threads: {listed}')
        if self.case.page_url is not None:
            lines.append(f'Page: {self.case.page_url}')
        return lines

    def render(self) -> str:
        sections = map(self.render_section, HEADINGS)
        return '\n'.join((*self.render_header(), *chain.from_iterable(sections)))


@dataclass(slots=True, kw_only=True, frozen=True)
class CheckReport:
    findings: tuple[Finding, ...]

    @property
    def has_failures(self) -> bool:
        return any(finding.state in FAILING_STATES for finding in self.findings)

    @property
    def summary(self) -> str:
        counted = tally_states(self.findings)
        return ', '.join(f'{counted[state]} {state}' for state in CITE_STATES)

    def describe(self, finding: Finding) -> str:
        moved = f', now at line {finding.moved_to}' if finding.moved_to is not None else ''
        return f'- [{finding.ref}] {finding.state}: `{finding.cite}`{moved}'

    def render(self) -> str:
        flagged = (finding for finding in self.findings if finding.state not in QUIET_STATES)
        lines = [
            f'checked {len(self.findings)} citations: {self.summary}',
            *map(self.describe, flagged),
        ]
        if self.has_failures:
            lines.append(
                'A changed or missing citation is no longer evidence. Verify the claim again, '
                'then retire the old entry with supersedes.'
            )
        return '\n'.join(lines)
