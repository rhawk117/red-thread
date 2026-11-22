"""The use cases of a case file: frame, add, check and show."""

from dataclasses import asdict, dataclass, field, replace
from typing import TYPE_CHECKING

from red_thread_casefile.domain import THREAD_NAME, Capabilities, Case, Cite, Entry
from red_thread_casefile.errors import (
    BatchRejectedError,
    CaseExistsError,
    InvalidThreadError,
    MisquotedCiteError,
    UnresolvedCiteError,
)
from red_thread_casefile.policy import CiteCheck, DraftPolicy, Finding, SupersedePolicy
from red_thread_casefile.redaction import create_secret_patterns
from red_thread_casefile.util import rank_languages
from red_thread_casefile.views import Board, BoardOptions

if TYPE_CHECKING:
    from red_thread_casefile.domain import CaseKind, Draft, Ledger
    from red_thread_casefile.errors import CaseFileError
    from red_thread_casefile.redaction import SecretPatterns
    from red_thread_casefile.store import CaseRepository, Clock, SourceTree

type CiteProblem = UnresolvedCiteError | MisquotedCiteError

TEXT_FIELDS = ('text', 'cite', 'quote', 'addr', 'rests_on', 'refute', 'diagram')
NAVIGATION_TOOL = 'agentlens'
EXCLUDED = '.red-thread/'


@dataclass(slots=True, kw_only=True, frozen=True)
class Framing:
    id: str
    target: str
    kind: CaseKind
    bar: str
    publish: bool = False


@dataclass(slots=True, kw_only=True, frozen=True)
class Batch:
    drafts: tuple[Draft, ...]
    round: int
    thread: str | None = None
    problems: tuple[CaseFileError, ...] = ()


@dataclass(slots=True, kw_only=True, frozen=True)
class Prepared:
    draft: Draft
    hits: int


@dataclass(slots=True, kw_only=True, frozen=True)
class Added:
    entries: tuple[Entry, ...]
    redactions: int


@dataclass(slots=True, kw_only=True, frozen=True)
class Stamp:
    at: str
    head: str | None
    round: int
    thread: str | None
    first_seq: int

    def apply(self, offset: int, draft: Draft) -> Entry:
        fields = {name: value for name, value in asdict(draft).items() if name != 'position'}
        return Entry(
            **fields,
            seq=self.first_seq + offset,
            round=self.round,
            thread=self.thread,
            at=self.at,
            head=self.head,
        )


@dataclass(slots=True, kw_only=True, frozen=True)
class Intake:
    tree: SourceTree
    patterns: SecretPatterns
    batch: Batch
    ledger: Ledger

    def probe(self, draft: Draft) -> CiteCheck | None:
        cite = Cite(raw=draft.cite or '')
        if cite.path is None or cite.line is None:
            return None
        lines = self.tree.read_lines(cite.path)
        return CiteCheck(quote=draft.quote or '', line=cite.line, lines=lines)

    def get_cite_problem(self, draft: Draft) -> CiteProblem | None:
        probe = self.probe(draft)
        if probe is None:
            return None

        if probe.cited_line is None:
            return UnresolvedCiteError(position=draft.position, cite=draft.cite or '')

        if draft.quote is not None and not probe.is_in_place:
            return MisquotedCiteError(
                position=draft.position, cite=draft.cite or '', found_at=probe.moved_to
            )

        return None

    def find_problem(self, draft: Draft) -> CaseFileError | None:
        thread = self.batch.thread
        policy = DraftPolicy(draft=draft, thread=thread)
        supersede = SupersedePolicy(draft=draft, known_refs=self.ledger.refs, thread=thread)
        return (
            policy.get_storage_problem()
            or supersede.get_supersede_problem()
            or self.get_cite_problem(draft)
        )

    def find_problems(self) -> tuple[CaseFileError, ...]:
        found = map(self.find_problem, self.batch.drafts)
        return tuple(problem for problem in found if problem is not None)

    def quote(self, draft: Draft) -> Draft:
        probe = self.probe(draft)
        if probe is None or draft.quote is not None:
            return draft
        return replace(draft, quote=probe.cited_line)

    def prepare(self, draft: Draft) -> Prepared:
        quoted = self.quote(draft)
        present = {name: value for name in TEXT_FIELDS if (value := getattr(quoted, name))}
        scrubbed = {name: self.patterns.scrub(value) for name, value in present.items()}
        clean = replace(quoted, **{name: found.text for name, found in scrubbed.items()})
        return Prepared(draft=clean, hits=sum(found.hits for found in scrubbed.values()))


@dataclass(slots=True, kw_only=True, frozen=True)
class CaseFile:
    repository: CaseRepository
    tree: SourceTree
    clock: Clock
    patterns: SecretPatterns = field(default_factory=create_secret_patterns)

    def frame(self, framing: Framing) -> Case:
        if self.repository.exists():
            raise CaseExistsError(case_id=framing.id)

        capabilities = Capabilities(
            languages=rank_languages(self.tree.list_files()),
            navigation_tool=self.tree.has_tool(NAVIGATION_TOOL),
        )
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
        self.repository.create(case)
        self.tree.exclude(EXCLUDED)
        return case

    def add(self, batch: Batch) -> Added:
        if batch.thread is not None and THREAD_NAME.fullmatch(batch.thread) is None:
            raise InvalidThreadError(thread=batch.thread)

        ledger = self.repository.read_ledger()
        intake = Intake(tree=self.tree, patterns=self.patterns, batch=batch, ledger=ledger)
        if problems := (*batch.problems, *intake.find_problems()):
            raise BatchRejectedError(problems=problems)

        stamp = Stamp(
            at=self.clock.now(),
            head=self.tree.get_head(),
            round=batch.round,
            thread=batch.thread,
            first_seq=ledger.count_in(batch.thread) + 1,
        )
        prepared = tuple(map(intake.prepare, batch.drafts))
        entries = tuple(stamp.apply(offset, item.draft) for offset, item in enumerate(prepared))
        self.repository.append(batch.thread, entries)
        return Added(entries=entries, redactions=sum(item.hits for item in prepared))

    def read_scrubbed(self, path: str) -> tuple[str, ...] | None:
        lines = self.tree.read_lines(path)
        if lines is None:
            return None
        return tuple(self.patterns.scrub(line).text for line in lines)

    def inspect(self, entry: Entry) -> Finding:
        cite = Cite(raw=entry.cite or '')
        if cite.path is None or cite.line is None:
            return Finding(ref=entry.ref, cite=cite.raw, state='unchecked')
        lines = self.read_scrubbed(cite.path)
        probe = CiteCheck(quote=entry.quote or '', line=cite.line, lines=lines)
        return Finding(
            ref=entry.ref, cite=cite.raw, state=probe.get_state(), moved_to=probe.moved_to
        )

    def check(self) -> tuple[Finding, ...]:
        cited = (entry for entry in self.repository.read_ledger().live if entry.cite is not None)
        return tuple(map(self.inspect, cited))

    def show(self, options: BoardOptions | None = None) -> str:
        board = Board(
            case=self.repository.read_case(),
            ledger=self.repository.read_ledger(),
            head=self.tree.get_head(),
            options=options or BoardOptions(),
            findings=self.check(),
        )
        return board.render()
