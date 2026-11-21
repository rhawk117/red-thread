"""The board, the documents and the check report: rendered from the ledger, never from memory."""

import sys
from collections import Counter
from dataclasses import dataclass, field
from itertools import chain
from typing import TYPE_CHECKING, Self

from red_thread_casefile.charts import create_case_map
from red_thread_casefile.domain import Cite
from red_thread_casefile.policy import CITE_STATES
from red_thread_casefile.util import squeeze

if TYPE_CHECKING:
    from red_thread_casefile.domain import Case, Entry, EntryKind, Ledger
    from red_thread_casefile.policy import Finding

SHORT_HEAD = 7
FAILING_STATES = ('changed', 'missing')
QUIET_STATES = ('ok', 'unchecked')
SECTIONS: tuple[tuple[EntryKind, str], ...] = (
    ('decision', 'Decided'),
    ('known', 'Known'),
    ('hypothesis', 'Hypotheses'),
    ('open', 'Open'),
    ('ruled_out', 'Ruled out'),
    ('next', 'Next'),
    ('resource', 'Resources'),
)


def list_caveats(entry: Entry) -> list[str]:
    labelled = (('rests on', entry.rests_on), ('refuted by', entry.refute))
    return [f'{label}: {value}' for label, value in labelled if value is not None]


def label_entry(entry: Entry) -> str:
    shown = entry.verdict is not None and entry.kind != 'known'
    verdict = f'{entry.verdict}: ' if shown else ''
    return f'{verdict}{squeeze(entry.text)}'


@dataclass(slots=True, kw_only=True, frozen=True)
class Item:
    text: str
    ref: str | None = None
    cite: str | None = None
    notes: tuple[str, ...] = ()
    flags: tuple[str, ...] = ()
    kind: EntryKind | None = None
    thread: str | None = None
    diagram: str | None = None


@dataclass(slots=True, kw_only=True, frozen=True)
class Section:
    title: str
    items: tuple[Item, ...] = ()
    prose: tuple[str, ...] = ()


@dataclass(slots=True, kw_only=True, frozen=True)
class Document:
    title: str
    summary: tuple[str, ...] = ()
    sections: tuple[Section, ...] = ()
    map_lines: tuple[str, ...] = ()


@dataclass(slots=True, kw_only=True, frozen=True)
class Annotator:
    head: str | None = None
    findings: tuple[Finding, ...] = ()

    def find(self, entry: Entry) -> Finding | None:
        return next((finding for finding in self.findings if finding.ref == entry.ref), None)

    def list_flags(self, entry: Entry) -> list[str]:
        flags: list[str] = []
        if entry.head != self.head:
            recorded = entry.head[:SHORT_HEAD] if entry.head is not None else 'no commit'
            flags.append(f'lead, recorded at {recorded}')

        finding = self.find(entry)
        if finding is not None and finding.state in FAILING_STATES:
            flags.append(f'citation {finding.state}')

        if finding is not None and finding.moved_to is not None:
            flags.append(f'citation moved to line {finding.moved_to}')

        return flags


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

    def create_item(self, entry: Entry) -> Item:
        return Item(
            text=label_entry(entry),
            ref=entry.ref,
            cite=entry.cite,
            notes=(*self.list_remarks(entry), entry.source),
            flags=tuple(self.annotator.list_flags(entry)),
            kind=entry.kind,
            thread=entry.thread,
            diagram=entry.diagram,
        )

    def render_section(self, kind: EntryKind, title: str) -> list[str]:
        entries = self.ledger.select(kind)
        if not entries:
            return []
        shown = entries[-self.options.per_section :]
        hidden = len(entries) - len(shown)
        lines = ['', f'## {title} ({len(entries)})']
        if hidden:
            lines.append(f'(+{hidden} earlier, shown by render --full)')
        lines.extend(map(self.describe, shown))
        return lines

    def render_header(self) -> list[str]:
        live = len(self.ledger.live)
        retired = len(self.ledger.entries) - live
        head = (self.head or 'none')[:SHORT_HEAD]
        lines = [
            f'# {self.case.id}',
            f'Target: {self.case.target}',
            f'Bar: {self.case.bar}',
            f'Kind: {self.case.kind} | Round: {self.ledger.last_round} | HEAD: {head}',
            f'Entries: {live} live, {retired} retired',
        ]
        threads = (f'{name} ({self.ledger.count_in(name)})' for name in self.ledger.threads)
        if listed := ', '.join(threads):
            lines.append(f'Threads: {listed}')
        if self.case.page_url is not None:
            lines.append(f'Page: {self.case.page_url}')
        return lines

    def render(self) -> str:
        sections = (self.render_section(kind, title) for kind, title in SECTIONS)
        return '\n'.join((*self.render_header(), *chain.from_iterable(sections)))

    def compose_section(self, kind: EntryKind, title: str) -> Section:
        entries = self.ledger.select(kind)
        items = tuple(map(self.create_item, entries))
        return Section(title=f'{title} ({len(entries)})', items=items)

    def compose(self) -> Document:
        sections = (self.compose_section(kind, title) for kind, title in SECTIONS)
        return Document(
            title=self.case.target,
            summary=(f'Case {self.case.id}', *self.render_header()[2:]),
            sections=tuple(section for section in sections if section.items),
            map_lines=create_case_map(self.ledger).render(),
        )


@dataclass(slots=True, kw_only=True, frozen=True)
class MarkdownWriter:
    document: Document

    def write_cite(self, cite: str) -> str:
        if Cite(raw=cite).is_url:
            return f' <{cite}>'
        return f' `{cite}`'

    def write_item(self, item: Item) -> str:
        remarks = '; '.join((*item.flags, *item.notes))
        noted = f' ({remarks})' if remarks else ''
        cite = self.write_cite(item.cite) if item.cite is not None else ''
        ref = f' [{item.ref}]' if item.ref is not None else ''
        return f'- {item.text}{noted}{cite}{ref}'

    def write_section(self, section: Section) -> list[str]:
        items = map(self.write_item, section.items)
        return ['', f'## {section.title}', '', *section.prose, *items]

    def render(self) -> str:
        sections = chain.from_iterable(map(self.write_section, self.document.sections))
        lines = (f'# {self.document.title}', '', *self.document.summary, *sections)
        return '\n'.join(lines) + '\n'


@dataclass(slots=True, kw_only=True, frozen=True)
class CheckReport:
    findings: tuple[Finding, ...]

    @property
    def has_failures(self) -> bool:
        return any(finding.state in FAILING_STATES for finding in self.findings)

    @property
    def summary(self) -> str:
        counted = Counter(finding.state for finding in self.findings)
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
