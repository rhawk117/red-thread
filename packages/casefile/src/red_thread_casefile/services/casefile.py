"""The use cases of a case file: frame it, read it, check it and show it."""

from dataclasses import dataclass, field
from itertools import chain
from typing import TYPE_CHECKING

from red_thread_core.dto import DTO
from red_thread_core.redaction import create_secret_patterns

from red_thread_casefile.domain import (
    STATE_DIRECTORY,
    TEXT_FIELDS,
    Capabilities,
    Case,
    CaseFinding,
    CaseKind,
    Citation,
    is_current,
)
from red_thread_casefile.errors import MalformedCaseError, SecretInFindingError
from red_thread_casefile.policy import (
    CitationCheck,
    CitationPolicy,
    CitationReader,
    FindingPolicy,
    SupersedePolicy,
    get_page_problem,
)
from red_thread_casefile.schemas import CaseFileSchema, load_record
from red_thread_casefile.util import rank_languages
from red_thread_casefile.views import Board, BoardOptions

if TYPE_CHECKING:
    from red_thread_core.codec import Codec
    from red_thread_core.redaction import SecretPatterns
    from red_thread_core.store import SourceTree
    from red_thread_core.timekeeping import Clock

    from red_thread_casefile.documents import Wording
    from red_thread_casefile.domain import CaseLedger, CaseRecord, LocatedFinding
    from red_thread_casefile.errors import CaseFileError
    from red_thread_casefile.schemas import CaseReading
    from red_thread_casefile.store import CaseRepository

type Problems = tuple[CaseFileError, ...]

EXCLUDED = f'{STATE_DIRECTORY}/'


class Framing(DTO, frozen=True, kw_only=True, gc=False):
    id: str
    target: str
    kind: CaseKind
    bar: str
    publish: bool = False


class Checked(DTO, frozen=True, kw_only=True, gc=False):
    problems: Problems
    citation_checks: tuple[CitationCheck, ...]


@dataclass(slots=True, kw_only=True, frozen=True)
class Inspector:
    tree: SourceTree
    patterns: SecretPatterns
    ledger: CaseLedger
    head: str | None

    def read_scrubbed(self, path: str) -> tuple[str, ...] | None:
        lines = self.tree.read_lines(path)
        if lines is None:
            return None
        return tuple(map(self.patterns.scrub_text, lines))

    def probe(self, finding: CaseFinding) -> CitationReader | None:
        citation = Citation(raw=finding.citation or '')
        if citation.path is None or citation.line is None:
            return None
        lines = self.read_scrubbed(citation.path)
        return CitationReader(quote=finding.quote or '', line=citation.line, lines=lines)

    def inspect(self, finding: CaseFinding) -> CitationCheck:
        probe = self.probe(finding)
        if probe is None or finding.quote is None:
            return CitationCheck(
                finding_id=finding.finding_id, citation=finding.citation or '', state='unchecked'
            )
        return CitationCheck(
            finding_id=finding.finding_id,
            citation=finding.citation or '',
            state=probe.get_state(),
            moved_to=probe.moved_to,
        )

    def find_citations(self) -> tuple[CitationCheck, ...]:
        cited = (finding for finding in self.ledger.live if finding.citation is not None)
        return tuple(map(self.inspect, cited))

    def get_citation_problem(self, located: LocatedFinding) -> CaseFileError | None:
        probe = self.probe(located.finding)
        if probe is None:
            return None
        policy = CitationPolicy(
            finding=located.finding,
            location=located.location,
            probe=probe,
            is_fresh=is_current(located.finding.head, self.head),
        )
        return policy.get_citation_problem()

    def find_secret_problems(self, located: LocatedFinding) -> tuple[SecretInFindingError, ...]:
        fields = (field for field in CaseFinding.fields() if field.encode_name in TEXT_FIELDS)
        present = ((field.encode_name, getattr(located.finding, field.name)) for field in fields)
        scrubbed = ((name, self.patterns.scrub(value)) for name, value in present if value)
        return tuple(
            SecretInFindingError(location=located.location, field=name, scrubbed=found.text)
            for name, found in scrubbed
            if found.hits
        )

    def find_problems(self, located: LocatedFinding) -> Problems:
        supersede = SupersedePolicy(
            finding=located.finding,
            location=located.location,
            known_finding_ids=self.ledger.finding_ids,
        ).get_supersede_problem()
        always = (*filter(None, (supersede,)), *self.find_secret_problems(located))
        if located.finding.finding_id in self.ledger.retired:
            return always

        rules = FindingPolicy(
            finding=located.finding, location=located.location
        ).get_finding_issues()
        citation = self.get_citation_problem(located)
        return (*rules, *filter(None, (citation,)), *always)


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

    def create_inspector(self, ledger: CaseLedger) -> Inspector:
        return Inspector(
            tree=self.tree, patterns=self.patterns, ledger=ledger, head=self.tree.get_head()
        )

    def find_citations(self, ledger: CaseLedger) -> tuple[CitationCheck, ...]:
        return self.create_inspector(ledger).find_citations()

    def check(self) -> Checked:
        reading = self.read()
        inspector = self.create_inspector(reading.ledger)
        found = chain.from_iterable(map(inspector.find_problems, reading.located))
        return Checked(
            problems=(*reading.problems, *find_case_problems(reading.case), *found),
            citation_checks=inspector.find_citations(),
        )

    def show(self, options: BoardOptions | None = None) -> str:
        record = self.load()
        board = Board(
            case=record.case,
            ledger=record.ledger,
            headings=self.wording.headings,
            head=self.tree.get_head(),
            options=options or BoardOptions(),
            citation_checks=self.find_citations(record.ledger),
        )
        return board.render()
