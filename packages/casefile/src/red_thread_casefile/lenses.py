"""Lens outputs: a selection picks and ranks live entries, and the ledger supplies their words."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from red_thread_casefile.documents import (
    Document,
    EntryBuilder,
    Note,
    Paragraph,
    PointList,
    Section,
    list_caveat_notes,
    list_entries_block,
    parse_line,
)
from red_thread_casefile.domain import PROGRAM, STATE_DIRECTORY, shorten_head
from red_thread_casefile.errors import LensOverBudgetError, UnknownSelectionRefError
from red_thread_casefile.util import squeeze
from red_thread_casefile.views import Annotator, CheckReport, describe_kind

if TYPE_CHECKING:
    from red_thread_casefile.documents import EntryNode
    from red_thread_casefile.domain import Case, Entry, EntryKind, Ledger
    from red_thread_casefile.policy import Finding

type LensName = Literal['brief', 'issue', 'handoff', 'report']
type FixedPart = Literal['goal', 'pointers', 'reading']

LENS_NAMES: tuple[LensName, ...] = ('brief', 'issue', 'handoff', 'report')
READING = (
    'Citations are pointers. Open the cited line before relying on a summary of it.',
    'An entry flagged as a lead was recorded at another commit. Verify it again first.',
    'An open entry is not established. Its rests on note names what it depends on.',
    'Square brackets hold the entry ref in the ledger, which has the full record.',
)


@dataclass(slots=True, kw_only=True, frozen=True)
class Part:
    title: str
    kind: EntryKind | None = None
    fixed: FixedPart | None = None


GOAL_SUMMARY = Part(title='Summary', fixed='goal')
POINTERS = Part(title='Pointers', fixed='pointers')
HOW_TO_READ = Part(title='How to read', fixed='reading')


@dataclass(slots=True, kw_only=True, frozen=True)
class Lens:
    name: LensName
    intro: str
    budget: int
    parts: tuple[Part, ...]


LENSES = (
    Lens(
        name='brief',
        intro='Brief of',
        budget=60,
        parts=(
            Part(title='Goal', fixed='goal'),
            Part(title='Decided', kind='decision'),
            Part(title='Constraints', kind='known'),
            Part(title='Ruled out', kind='ruled_out'),
            Part(title='Open', kind='open'),
            POINTERS,
            HOW_TO_READ,
        ),
    ),
    Lens(
        name='issue',
        intro='Raised from',
        budget=80,
        parts=(
            GOAL_SUMMARY,
            Part(title='Findings', kind='known'),
            Part(title='Open questions', kind='open'),
            Part(title='Ruled out', kind='ruled_out'),
            Part(title='Next steps', kind='next'),
            Part(title='References', kind='resource'),
            POINTERS,
        ),
    ),
    Lens(
        name='handoff',
        intro='Handoff of',
        budget=40,
        parts=(
            Part(title='Where this stands', fixed='goal'),
            Part(title='Decided', kind='decision'),
            Part(title='Start here', kind='next'),
            Part(title='Open', kind='open'),
            Part(title='Hypotheses', kind='hypothesis'),
            POINTERS,
            HOW_TO_READ,
        ),
    ),
    Lens(
        name='report',
        intro='Report on',
        budget=200,
        parts=(
            GOAL_SUMMARY,
            Part(title='Decided', kind='decision'),
            Part(title='Findings', kind='known'),
            Part(title='Hypotheses', kind='hypothesis'),
            Part(title='Ruled out', kind='ruled_out'),
            Part(title='Open', kind='open'),
            Part(title='Next steps', kind='next'),
            Part(title='Resources', kind='resource'),
            POINTERS,
            HOW_TO_READ,
        ),
    ),
)


def get_lens(name: LensName) -> Lens:
    return next(lens for lens in LENSES if lens.name == name)


def count_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


@dataclass(slots=True, kw_only=True, frozen=True)
class Selection:
    title: str | None = None
    goal: str | None = None
    include: tuple[str, ...] | None = None
    blocking: tuple[str, ...] | None = None

    @property
    def named(self) -> tuple[str, ...]:
        return (*(self.include or ()), *(self.blocking or ()))

    def is_blocking(self, entry: Entry) -> bool:
        return entry.ref in (self.blocking or ())

    def admits(self, entry: Entry) -> bool:
        if self.include is None or entry.kind == 'decision':
            return True
        return entry.ref in self.include or self.is_blocking(entry)

    def rank(self, entry: Entry) -> tuple[bool, int]:
        chosen = self.include or ()
        position = chosen.index(entry.ref) if entry.ref in chosen else len(chosen)
        return (not self.is_blocking(entry), position)


@dataclass(slots=True, kw_only=True, frozen=True)
class Edition:
    case: Case
    ledger: Ledger
    head: str | None = None
    findings: tuple[Finding, ...] = ()

    @property
    def short_head(self) -> str:
        return shorten_head(self.head)

    @property
    def annotator(self) -> Annotator:
        return Annotator(head=self.head, findings=self.findings)


@dataclass(slots=True, kw_only=True, frozen=True)
class Composer:
    lens: Lens
    selection: Selection
    edition: Edition

    def get_selection_problem(self) -> UnknownSelectionRefError | None:
        live = {entry.ref for entry in self.edition.ledger.live}
        unknown = next((ref for ref in self.selection.named if ref not in live), None)
        if unknown is None:
            return None
        return UnknownSelectionRefError(ref=unknown)

    def get_budget_problem(self, text: str) -> LensOverBudgetError | None:
        lines = count_lines(text)
        if lines <= self.lens.budget:
            return None
        return LensOverBudgetError(lens=self.lens.name, lines=lines, budget=self.lens.budget)

    def select(self, kind: EntryKind) -> tuple[Entry, ...]:
        admitted = filter(self.selection.admits, self.edition.ledger.select(kind))
        return tuple(sorted(admitted, key=self.selection.rank))

    def list_notes(self, entry: Entry) -> tuple[Note, ...]:
        notes = list_caveat_notes(entry)
        if self.selection.blocking is None or entry.kind != 'open':
            return notes
        urgency = 'blocking' if self.selection.is_blocking(entry) else 'not blocking'
        return (Note(kind='urgency', value=urgency), *notes)

    def create_entry(self, entry: Entry) -> EntryNode:
        builder = EntryBuilder(annotator=self.edition.annotator)
        return builder.build(entry, self.list_notes(entry))

    def list_pointers(self) -> PointList:
        case = self.edition.case
        location = f'{STATE_DIRECTORY}/{case.id}'
        checked = CheckReport(findings=self.edition.findings).summary
        pointers = [
            f'Ledger: `{location}/ledger.jsonl`, with one file per thread under `threads/`.',
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
            entries = tuple(map(self.create_entry, self.select(part.kind)))
            blocks = list_entries_block(entries)
            note = describe_kind(part.kind)
            return Section(title=part.title, blocks=blocks, kind=part.kind, note=note)

        if part.fixed == 'goal':
            return Section(title=part.title, blocks=(self.write_goal(),))

        if part.fixed == 'reading':
            reading = PointList(points=tuple(map(parse_line, READING)))
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
