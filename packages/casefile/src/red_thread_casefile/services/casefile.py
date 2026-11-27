"""The use cases of a case file: frame it, read it, check it and show it."""

from dataclasses import dataclass, field
from itertools import chain
from typing import TYPE_CHECKING

from red_thread_core.redaction import create_secret_patterns

from red_thread_casefile.domain import (
    STATE_DIRECTORY,
    TEXT_FIELDS,
    Capabilities,
    Case,
    Cite,
    is_current,
)
from red_thread_casefile.errors import MalformedCaseError, SecretInEntryError
from red_thread_casefile.policy import (
    CiteCheck,
    CitePolicy,
    EntryPolicy,
    Finding,
    SupersedePolicy,
    get_page_problem,
)
from red_thread_casefile.schemas import CaseFileSchema, load_record
from red_thread_casefile.util import rank_languages
from red_thread_casefile.views import Board, BoardOptions

if TYPE_CHECKING:
    from red_thread_core.codec import Codec
    from red_thread_core.redaction import SecretPatterns
    from red_thread_core.store import Clock, SourceTree

    from red_thread_casefile.documents import Wording
    from red_thread_casefile.domain import CaseKind, CaseRecord, Entry, Ledger, Placed
    from red_thread_casefile.errors import CaseFileError
    from red_thread_casefile.schemas import CaseReading
    from red_thread_casefile.store import CaseRepository

type Problems = tuple[CaseFileError, ...]

EXCLUDED = f'{STATE_DIRECTORY}/'


@dataclass(slots=True, kw_only=True, frozen=True)
class Framing:
    id: str
    target: str
    kind: CaseKind
    bar: str
    publish: bool = False


@dataclass(slots=True, kw_only=True, frozen=True)
class Checked:
    problems: Problems
    findings: tuple[Finding, ...]


@dataclass(slots=True, kw_only=True, frozen=True)
class Inspector:
    tree: SourceTree
    patterns: SecretPatterns
    ledger: Ledger
    head: str | None

    def read_scrubbed(self, path: str) -> tuple[str, ...] | None:
        lines = self.tree.read_lines(path)
        if lines is None:
            return None
        return tuple(map(self.patterns.scrub_text, lines))

    def probe(self, entry: Entry) -> CiteCheck | None:
        cite = Cite(raw=entry.cite or '')
        if cite.path is None or cite.line is None:
            return None
        lines = self.read_scrubbed(cite.path)
        return CiteCheck(quote=entry.quote or '', line=cite.line, lines=lines)

    def inspect(self, entry: Entry) -> Finding:
        probe = self.probe(entry)
        if probe is None or entry.quote is None:
            return Finding(ref=entry.ref, cite=entry.cite or '', state='unchecked')
        return Finding(
            ref=entry.ref, cite=entry.cite or '', state=probe.get_state(), moved_to=probe.moved_to
        )

    def find_citations(self) -> tuple[Finding, ...]:
        cited = (entry for entry in self.ledger.live if entry.cite is not None)
        return tuple(map(self.inspect, cited))

    def get_cite_problem(self, placed: Placed) -> CaseFileError | None:
        probe = self.probe(placed.entry)
        if probe is None:
            return None
        policy = CitePolicy(
            entry=placed.entry,
            spot=placed.spot,
            probe=probe,
            is_fresh=is_current(placed.entry.head, self.head),
        )
        return policy.get_cite_problem()

    def find_secret_problems(self, placed: Placed) -> tuple[SecretInEntryError, ...]:
        present = ((name, getattr(placed.entry, name)) for name in TEXT_FIELDS)
        scrubbed = ((name, self.patterns.scrub(value)) for name, value in present if value)
        return tuple(
            SecretInEntryError(spot=placed.spot, field=name, scrubbed=found.text)
            for name, found in scrubbed
            if found.hits
        )

    def find_problems(self, placed: Placed) -> Problems:
        supersede = SupersedePolicy(
            entry=placed.entry, spot=placed.spot, known_refs=self.ledger.refs
        ).get_supersede_problem()
        always = (*filter(None, (supersede,)), *self.find_secret_problems(placed))
        if placed.entry.ref in self.ledger.retired:
            return always

        rules = EntryPolicy(entry=placed.entry, spot=placed.spot).get_entry_issues()
        cite = self.get_cite_problem(placed)
        return (*rules, *filter(None, (cite,)), *always)


def find_case_problems(case: Case | None) -> Problems:
    if case is None or case.page_url is None:
        return ()
    return tuple(filter(None, (get_page_problem(case.page_url),)))


@dataclass(slots=True, kw_only=True, frozen=True)
class CaseFile:
    repository: CaseRepository
    tree: SourceTree
    clock: Clock
    wording: Wording
    codec: Codec
    patterns: SecretPatterns = field(default_factory=create_secret_patterns)

    @property
    def schema(self) -> CaseFileSchema:
        return CaseFileSchema(codec=self.codec)

    def frame(self, framing: Framing) -> Case:
        capabilities = Capabilities(languages=rank_languages(self.tree.list_files()))
        case = Case(
            id=framing.id,
            target=framing.target,
            kind=framing.kind,
            bar=framing.bar,
            publish=framing.publish,
            created=self.clock.now(),
            head=self.tree.get_head(),
            capabilities=capabilities,
        )
        self.repository.create(self.schema.write(case))
        self.tree.exclude(EXCLUDED)
        return case

    def read(self) -> CaseReading:
        return self.schema.read(self.repository.read())

    def load(self) -> CaseRecord:
        record = load_record(self.read())
        if isinstance(record, MalformedCaseError):
            raise record
        return record

    def create_inspector(self, ledger: Ledger) -> Inspector:
        return Inspector(
            tree=self.tree, patterns=self.patterns, ledger=ledger, head=self.tree.get_head()
        )

    def find_citations(self, ledger: Ledger) -> tuple[Finding, ...]:
        return self.create_inspector(ledger).find_citations()

    def check(self) -> Checked:
        reading = self.read()
        inspector = self.create_inspector(reading.ledger)
        found = chain.from_iterable(map(inspector.find_problems, reading.placed))
        return Checked(
            problems=(*reading.problems, *find_case_problems(reading.case), *found),
            findings=inspector.find_citations(),
        )

    def show(self, options: BoardOptions | None = None) -> str:
        record = self.load()
        board = Board(
            case=record.case,
            ledger=record.ledger,
            headings=self.wording.headings,
            head=self.tree.get_head(),
            options=options or BoardOptions(),
            findings=self.find_citations(record.ledger),
        )
        return board.render()
