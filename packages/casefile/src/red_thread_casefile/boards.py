"""The board as a page: each live entry with its details, the case facts and what was retired."""

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

from red_thread_casefile.assets import read_asset
from red_thread_casefile.charts import create_case_map
from red_thread_casefile.documents import (
    EntryBuilder,
    EntryList,
    Note,
    list_caveat_notes,
    list_entries_block,
)
from red_thread_casefile.domain import NO_HEAD, date_of, shorten_head
from red_thread_casefile.policy import CITE_STATES, tally_states
from red_thread_casefile.terms import BOARD_TERMS
from red_thread_casefile.views import HEADINGS

if TYPE_CHECKING:
    from red_thread_casefile.documents import EntryNode
    from red_thread_casefile.domain import Entry
    from red_thread_casefile.views import Board, Heading

MAP_NOTE = (
    'Each thread as a line of its entries, with an arrow from an entry to the one it retired.'
)
RETIRED_NOTE = (
    'Entries a later entry replaced. The ledger keeps them and the sections leave them out.'
)


def create_fact(label: str, value: str, *, wide: bool = False) -> Fact:
    return Fact(label=label, value=parse_value(value), wide=wide)


@dataclass(slots=True, kw_only=True, frozen=True)
class BoardPage:
    board: Board

    def list_retirers(self, entry: Entry) -> list[str]:
        return [other.ref for other in self.board.ledger.entries if entry.ref in other.supersedes]

    @property
    def builder(self) -> EntryBuilder:
        return EntryBuilder(annotator=self.board.annotator)

    def list_notes(self, entry: Entry) -> tuple[Note, ...]:
        retirers = ', '.join(self.list_retirers(entry))
        retires = ', '.join(entry.supersedes)
        retired_by = (Note(kind='retired_by', value=retirers),) if retirers else ()
        retiring = (Note(kind='retires', value=retires),) if retires else ()
        source = Note(kind='source', value=entry.source)
        return (*retired_by, *list_caveat_notes(entry), *retiring, source)

    def create_entry(self, entry: Entry) -> EntryNode:
        return self.builder.build(entry, self.list_notes(entry))

    def compose_section(self, heading: Heading) -> Section:
        entries = tuple(map(self.create_entry, self.board.ledger.select(heading.kind)))
        blocks = list_entries_block(entries)
        return Section(
            title=heading.title, blocks=blocks, kind=heading.kind, note=heading.note, column=True
        )

    def compose_map(self) -> tuple[Section, ...]:
        lines = create_case_map(self.board.ledger).render()
        if not lines:
            return ()
        chart = Flowchart(lines=(read_asset('map.mmd').rstrip(), *lines))
        return (Section(title='Map', blocks=(chart,), note=MAP_NOTE),)

    def compose_retired(self) -> tuple[Section, ...]:
        ledger = self.board.ledger
        retired = (entry for entry in ledger.entries if entry.ref in ledger.retired)
        entries = tuple(map(self.create_entry, retired))
        if not entries:
            return ()
        blocks = (EntryList(entries=entries),)
        return (Section(title='Retired', blocks=blocks, note=RETIRED_NOTE, folded=True),)

    def count_states(self) -> str:
        counted = tally_states(self.board.findings)
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
            create_fact('Created', date_of(case.created)),
            create_fact('Languages', ', '.join(case.capabilities.languages) or NO_HEAD),
            create_fact('Entries', f'{live} live, {len(ledger.entries) - live} retired'),
            create_fact('Threads', ledger.describe_threads() or NO_HEAD),
            create_fact('Citations', self.count_states(), wide=True),
        ]
        if case.page_url is not None:
            facts.append(create_fact('Page', case.page_url, wide=True))
        return tuple(facts)

    def compose(self) -> Document:
        sections = map(self.compose_section, HEADINGS)
        return Document(
            title=self.board.case.target,
            summary=(parse_line(f'Case {self.board.case.id}'),),
            facts=self.list_facts(),
            sections=tuple(section for section in sections if section.blocks),
            appendix=(*self.compose_map(), *self.compose_retired()),
            terms=BOARD_TERMS,
        )
