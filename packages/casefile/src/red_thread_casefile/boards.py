"""The board as a page: each live entry with its details, the case facts and what was retired."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_casefile.charts import create_case_map
from red_thread_casefile.domain import NO_HEAD, date_of, shorten_head
from red_thread_casefile.policy import CITE_STATES, tally_states
from red_thread_casefile.util import squeeze
from red_thread_casefile.views import (
    HEADINGS,
    Document,
    Fact,
    Item,
    Section,
    get_shown_verdict,
)

if TYPE_CHECKING:
    from red_thread_casefile.domain import Entry
    from red_thread_casefile.views import Board, Heading


@dataclass(slots=True, kw_only=True, frozen=True)
class BoardPage:
    board: Board

    def list_retirers(self, entry: Entry) -> list[str]:
        return [other.ref for other in self.board.ledger.entries if entry.ref in other.supersedes]

    def list_notes(self, entry: Entry) -> list[str]:
        retirers = ', '.join(self.list_retirers(entry))
        retired = [f'retired by {retirers}'] if retirers else []
        return [*retired, *self.board.list_remarks(entry), entry.source]

    def create_item(self, entry: Entry) -> Item:
        annotator = self.board.annotator
        return Item(
            text=squeeze(entry.text),
            ref=entry.ref,
            cite=entry.cite,
            notes=tuple(self.list_notes(entry)),
            flags=tuple(annotator.list_lead_flags(entry)),
            kind=entry.kind,
            thread=entry.thread,
            diagram=entry.diagram,
            verdict=get_shown_verdict(entry),
            round=entry.round,
            at=entry.at,
            quote=entry.quote,
            finding=annotator.find(entry),
        )

    def compose_section(self, heading: Heading) -> Section:
        items = tuple(map(self.create_item, self.board.ledger.select(heading.kind)))
        return Section(title=heading.title, items=items, kind=heading.kind, note=heading.note)

    def count_states(self) -> str:
        counted = tally_states(self.board.findings)
        states = (f'{counted[state]} {state}' for state in CITE_STATES if counted[state])
        return ', '.join(states) or NO_HEAD

    def list_facts(self) -> tuple[Fact, ...]:
        case = self.board.case
        ledger = self.board.ledger
        live = len(ledger.live)
        facts = [
            Fact(label='Bar', value=case.bar, wide=True),
            Fact(label='Kind', value=case.kind),
            Fact(label='Round', value=str(ledger.last_round)),
            Fact(label='Commit', value=shorten_head(self.board.head)),
            Fact(label='Created', value=date_of(case.created)),
            Fact(label='Languages', value=', '.join(case.capabilities.languages) or NO_HEAD),
            Fact(label='Entries', value=f'{live} live, {len(ledger.entries) - live} retired'),
            Fact(label='Threads', value=ledger.describe_threads() or NO_HEAD),
            Fact(label='Citations', value=self.count_states(), wide=True),
        ]
        if case.page_url is not None:
            facts.append(Fact(label='Page', value=case.page_url, wide=True))
        return tuple(facts)

    def compose(self) -> Document:
        ledger = self.board.ledger
        sections = map(self.compose_section, HEADINGS)
        retired = (entry for entry in ledger.entries if entry.ref in ledger.retired)
        return Document(
            title=self.board.case.target,
            summary=(f'Case {self.board.case.id}',),
            sections=tuple(section for section in sections if section.items),
            map_lines=create_case_map(ledger).render(),
            facts=self.list_facts(),
            retired=tuple(map(self.create_item, retired)),
        )
