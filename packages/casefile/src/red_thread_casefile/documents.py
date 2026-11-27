"""The case file's nodes in the document tree: a finding with its citation, notes and lead flag."""

from dataclasses import dataclass
from itertools import chain
from typing import TYPE_CHECKING, Literal

from red_thread_core.documents import Line, Term, parse_line
from red_thread_core.dto import DTO
from red_thread_core.util import squeeze

from red_thread_casefile.domain import Citation, FindingKind, Verdict
from red_thread_casefile.policy import CitationCheck
from red_thread_casefile.views import Heading, describe_lead, get_shown_verdict
from red_thread_casefile.writers.markdown import write_markdown_finding
from red_thread_casefile.writers.markup import write_findings

if TYPE_CHECKING:
    from red_thread_core.documents import Block, Document, Section
    from red_thread_core.elements import Element

    from red_thread_casefile.domain import CaseFinding
    from red_thread_casefile.views import Annotator

type NoteKind = Literal['rests_on', 'refuted_by', 'retires', 'retired_by', 'urgency', 'source']


class Note(DTO, frozen=True, kw_only=True, gc=False):
    kind: NoteKind
    text: str


class Wording(DTO, frozen=True, kw_only=True, forbid_unknown_fields=True):
    headings: tuple[Heading, ...]
    prefixes: dict[NoteKind, str]
    map_note: str
    retired_note: str
    terms: tuple[Term, ...]

    def describe_kind(self, kind: FindingKind) -> str:
        return next(heading.note for heading in self.headings if heading.kind == kind)

    def write_note(self, kind: NoteKind, value: str) -> Note:
        return Note(kind=kind, text=f'{self.prefixes[kind]}{value}')

    def list_caveat_notes(self, finding: CaseFinding) -> tuple[Note, ...]:
        rests_on = finding.rests_on
        refuted_if = finding.refuted_if
        resting = (self.write_note('rests_on', rests_on),) if rests_on is not None else ()
        refuted = (self.write_note('refuted_by', refuted_if),) if refuted_if is not None else ()
        return (*resting, *refuted)


class CitationNode(DTO, frozen=True, kw_only=True, gc=False):
    target: str
    quote: str | None = None
    citation_check: CitationCheck | None = None

    @property
    def is_url(self) -> bool:
        return Citation(raw=self.target).is_url


class FindingNode(DTO, frozen=True, kw_only=True, gc=False):
    finding_id: str
    kind: FindingKind
    claim: Line
    thread: str | None = None
    verdict: Verdict | None = None
    round: int
    at: str
    citation_node: CitationNode | None = None
    notes: tuple[Note, ...] = ()
    lead: str | None = None
    diagram: str | None = None

    @property
    def flags(self) -> tuple[str, ...]:
        if self.lead is None:
            return ()
        return (describe_lead(self.lead),)


class FindingList(DTO, frozen=True, kw_only=True, gc=False):
    findings: tuple[FindingNode, ...]

    @property
    def count(self) -> int:
        return len(self.findings)

    def write_html(self) -> Element | None:
        return write_findings(self.findings)

    def write_markdown(self) -> tuple[str, ...]:
        return tuple(map(write_markdown_finding, self.findings))


def list_section_findings(section: Section) -> tuple[FindingNode, ...]:
    lists = (block.findings for block in section.blocks if isinstance(block, FindingList))
    return tuple(chain.from_iterable(lists))


def list_document_findings(document: Document) -> tuple[FindingNode, ...]:
    return tuple(chain.from_iterable(map(list_section_findings, document.sections)))


def list_findings_block(findings: tuple[FindingNode, ...]) -> tuple[Block, ...]:
    if not findings:
        return ()
    return (FindingList(findings=findings),)


@dataclass(slots=True, kw_only=True, frozen=True)
class FindingNodeBuilder:
    annotator: Annotator

    def create_citation(self, finding: CaseFinding) -> CitationNode | None:
        if finding.citation is None:
            return None
        return CitationNode(
            target=finding.citation,
            quote=finding.quote,
            citation_check=self.annotator.find(finding),
        )

    def build(self, finding: CaseFinding, notes: tuple[Note, ...] = ()) -> FindingNode:
        return FindingNode(
            finding_id=finding.finding_id,
            kind=finding.kind,
            claim=parse_line(squeeze(finding.text)),
            round=finding.round,
            at=finding.at,
            thread=finding.thread,
            verdict=get_shown_verdict(finding),
            citation_node=self.create_citation(finding),
            notes=notes,
            lead=self.annotator.get_recorded_head(finding),
            diagram=finding.diagram,
        )
