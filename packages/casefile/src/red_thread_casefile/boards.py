"""The board as a page: each live finding with its details, the case facts and what was retired."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_core.documents import (
    Document,
    Fact,
    Flowchart,
    Section,
    parse_line,
    parse_value,
)

from red_thread_casefile.charts import create_case_map
from red_thread_casefile.documents import FindingList, FindingNodeBuilder, list_findings_block
from red_thread_casefile.domain import NO_HEAD, shorten_head
from red_thread_casefile.packaged import read_asset
from red_thread_casefile.policy import CITE_STATES, tally_states

if TYPE_CHECKING:
    from red_thread_casefile.documents import FindingNode, Note, Wording
    from red_thread_casefile.domain import CaseFinding
    from red_thread_casefile.views import Board, Heading


def create_fact(label: str, value: str, *, wide: bool = False) -> Fact:
    return Fact(label=label, value=parse_value(value), wide=wide)


@dataclass(slots=True, kw_only=True, frozen=True)
class BoardPage:
    board: Board
    wording: Wording

    def list_retirers(self, finding: CaseFinding) -> list[str]:
        return [
            other.finding_id
            for other in self.board.ledger.findings
            if finding.finding_id in other.supersedes
        ]

    @property
    def builder(self) -> FindingNodeBuilder:
        return FindingNodeBuilder(annotator=self.board.annotator)

    def list_notes(self, finding: CaseFinding) -> tuple[Note, ...]:
        retirers = ', '.join(self.list_retirers(finding))
        retires = ', '.join(finding.supersedes)
        wording = self.wording
        retired_by = (wording.write_note('retired_by', retirers),) if retirers else ()
        retiring = (wording.write_note('retires', retires),) if retires else ()
        source = wording.write_note('source', finding.source)
        return (*retired_by, *wording.list_caveat_notes(finding), *retiring, source)

    def create_finding(self, finding: CaseFinding) -> FindingNode:
        return self.builder.build(finding, self.list_notes(finding))

    def compose_section(self, heading: Heading) -> Section:
        findings = tuple(map(self.create_finding, self.board.ledger.select(heading.kind)))
        blocks = list_findings_block(findings)
        return Section(
            title=heading.title, blocks=blocks, kind=heading.kind, note=heading.note, column=True
        )

    def compose_map(self) -> tuple[Section, ...]:
        lines = create_case_map(self.board.ledger).render()
        if not lines:
            return ()
        chart = Flowchart(lines=(read_asset('map.mmd').rstrip(), *lines))
        return (Section(title='Map', blocks=(chart,), note=self.wording.map_note),)

    def compose_retired(self) -> tuple[Section, ...]:
        ledger = self.board.ledger
        retired = (finding for finding in ledger.findings if finding.finding_id in ledger.retired)
        findings = tuple(map(self.create_finding, retired))
        if not findings:
            return ()
        blocks = (FindingList(findings=findings),)
        note = self.wording.retired_note
        return (Section(title='Retired', blocks=blocks, note=note, folded=True),)

    def count_states(self) -> str:
        counted = tally_states(self.board.citation_checks)
        states = (f'{counted[state]} {state}' for state in CITE_STATES if counted[state])
        return ', '.join(states) or NO_HEAD

    def list_facts(self) -> tuple[Fact, ...]:
        case = self.board.case
        ledger = self.board.ledger
        live = len(ledger.live)
        facts = [
            create_fact('Bar', case.bar, wide=True),
            create_fact('Kind', case.kind),
            create_fact('Round', str(ledger.last_round)),
            create_fact('Commit', shorten_head(self.board.head)),
            create_fact('Created', case.created.date().isoformat()),
            create_fact('Languages', ', '.join(case.capabilities.languages) or NO_HEAD),
            create_fact('Findings', f'{live} live, {len(ledger.findings) - live} retired'),
            create_fact('Threads', ledger.describe_threads() or NO_HEAD),
            create_fact('Citations', self.count_states(), wide=True),
        ]
        if case.page_url is not None:
            facts.append(create_fact('Page', case.page_url, wide=True))
        return tuple(facts)

    def compose(self) -> Document:
        sections = map(self.compose_section, self.wording.headings)
        return Document(
            title=self.board.case.target,
            summary=(parse_line(f'Case {self.board.case.id}'),),
            facts=self.list_facts(),
            sections=tuple(section for section in sections if section.blocks),
            appendix=(*self.compose_map(), *self.compose_retired()),
            terms=self.wording.terms,
        )
