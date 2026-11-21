"""Lens outputs: a plan selects and ranks live entries, and the ledger supplies their words."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from red_thread_casefile.errors import LensOverBudgetError, UnknownPlanRefError
from red_thread_casefile.util import squeeze
from red_thread_casefile.views import (
    SHORT_HEAD,
    Annotator,
    CheckReport,
    Document,
    Item,
    Section,
    list_caveats,
)

if TYPE_CHECKING:
    from red_thread_casefile.domain import Case, Entry, EntryKind, Ledger
    from red_thread_casefile.policy import Finding

type LensName = Literal['brief', 'issue', 'handoff', 'report']
type FixedPart = Literal['goal', 'pointers', 'reading']

LENS_NAMES: tuple[LensName, ...] = ('brief', 'issue', 'handoff', 'report')
READING = (
    Item(text='Citations are pointers. Open the cited line before relying on a summary of it.'),
    Item(text='An entry flagged as a lead was recorded at another commit. Verify it again first.'),
    Item(text='An open entry is not established. Its rests on note names what it depends on.'),
    Item(text='Square brackets hold the entry ref in the ledger, which has the full record.'),
)


@dataclass(slots=True, kw_only=True, frozen=True)
class Part:
    title: str
    kind: EntryKind | None = None
    fixed: FixedPart | None = None


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
            Part(title='Pointers', fixed='pointers'),
            Part(title='How to read', fixed='reading'),
        ),
    ),
    Lens(
        name='issue',
        intro='Raised from',
        budget=80,
        parts=(
            Part(title='Summary', fixed='goal'),
            Part(title='Findings', kind='known'),
            Part(title='Open questions', kind='open'),
            Part(title='Ruled out', kind='ruled_out'),
            Part(title='Next steps', kind='next'),
            Part(title='References', kind='resource'),
            Part(title='Pointers', fixed='pointers'),
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
            Part(title='Pointers', fixed='pointers'),
            Part(title='How to read', fixed='reading'),
        ),
    ),
    Lens(
        name='report',
        intro='Report on',
        budget=200,
        parts=(
            Part(title='Summary', fixed='goal'),
            Part(title='Decided', kind='decision'),
            Part(title='Findings', kind='known'),
            Part(title='Hypotheses', kind='hypothesis'),
            Part(title='Ruled out', kind='ruled_out'),
            Part(title='Open', kind='open'),
            Part(title='Next steps', kind='next'),
            Part(title='Resources', kind='resource'),
            Part(title='Pointers', fixed='pointers'),
            Part(title='How to read', fixed='reading'),
        ),
    ),
)


def get_lens(name: LensName) -> Lens:
    return next(lens for lens in LENSES if lens.name == name)


def count_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


@dataclass(slots=True, kw_only=True, frozen=True)
class Plan:
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
        return (self.head or 'none')[:SHORT_HEAD]

    @property
    def annotator(self) -> Annotator:
        return Annotator(head=self.head, findings=self.findings)


@dataclass(slots=True, kw_only=True, frozen=True)
class Composer:
    lens: Lens
    plan: Plan
    edition: Edition

    def get_plan_problem(self) -> UnknownPlanRefError | None:
        live = {entry.ref for entry in self.edition.ledger.live}
        unknown = next((ref for ref in self.plan.named if ref not in live), None)
        if unknown is None:
            return None
        return UnknownPlanRefError(ref=unknown)

    def get_budget_problem(self, text: str) -> LensOverBudgetError | None:
        lines = count_lines(text)
        if lines <= self.lens.budget:
            return None
        return LensOverBudgetError(lens=self.lens.name, lines=lines, budget=self.lens.budget)

    def select(self, kind: EntryKind) -> tuple[Entry, ...]:
        admitted = filter(self.plan.admits, self.edition.ledger.select(kind))
        return tuple(sorted(admitted, key=self.plan.rank))

    def list_notes(self, entry: Entry) -> list[str]:
        notes = list_caveats(entry)
        if self.plan.blocking is None or entry.kind != 'open':
            return notes
        urgency = 'blocking' if self.plan.is_blocking(entry) else 'not blocking'
        return [urgency, *notes]

    def create_item(self, entry: Entry) -> Item:
        return Item(
            text=squeeze(entry.text),
            ref=entry.ref,
            cite=entry.cite,
            notes=tuple(self.list_notes(entry)),
            flags=tuple(self.edition.annotator.list_flags(entry)),
            kind=entry.kind,
            thread=entry.thread,
            diagram=entry.diagram,
        )

    def list_pointers(self) -> tuple[Item, ...]:
        case = self.edition.case
        location = f'.red-thread/{case.id}'
        checked = CheckReport(findings=self.edition.findings).summary
        pointers = [
            f'Ledger: `{location}/ledger.jsonl`, with one file per thread under `threads/`.',
            f'Citations checked at commit {self.edition.short_head}: {checked}.',
            f'Check again with the red-thread plugin: `casefile.sh check --case {location}`',
        ]
        if case.page_url is not None:
            pointers.append(f'Board: {case.page_url}')
        return tuple(Item(text=pointer) for pointer in pointers)

    def write_goal(self) -> tuple[str, ...]:
        case = self.edition.case
        if self.plan.goal is not None:
            return (squeeze(self.plan.goal),)
        return (f'{case.target} The bar for an answer: {case.bar}',)

    def compose_part(self, part: Part) -> Section:
        if part.kind is not None:
            items = tuple(map(self.create_item, self.select(part.kind)))
            return Section(title=part.title, items=items)

        if part.fixed == 'goal':
            return Section(title=part.title, prose=self.write_goal())

        if part.fixed == 'reading':
            return Section(title=part.title, items=READING)

        return Section(title=part.title, items=self.list_pointers())

    def compose(self) -> Document:
        case = self.edition.case
        ledger = self.edition.ledger
        sections = map(self.compose_part, self.lens.parts)
        summary = (
            f'{self.lens.intro} case `{case.id}` ({case.kind}), round {ledger.last_round}, '
            f'at commit {self.edition.short_head}.'
        )
        return Document(
            title=squeeze(self.plan.title or case.target),
            summary=(summary,),
            sections=tuple(section for section in sections if section.items or section.prose),
        )
