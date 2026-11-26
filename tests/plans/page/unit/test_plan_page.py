"""PlanPage: each worktree's stack of tickets, marked against the revision before it."""

from dataclasses import dataclass
from itertools import chain
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from msgspec.structs import replace
from red_thread_core.documents import CodeListing, Flowchart
from red_thread_plans.domain import Interface, Mitigate, Risk
from red_thread_plans.filters import list_tickets, render_plan_page
from red_thread_plans.nodes import TicketList

from tests.casefile.pages.html_reading import list_chip_groups, list_facts
from tests.casefile.writers.reading import render_markdown, render_page
from tests.params import as_params
from tests.plans.revisions.builders import (
    add_tickets,
    create_plan_document,
    create_ticket_draft,
    create_valid_draft,
    replace_ticket,
    stamp_plan,
)
from tests.plans.revisions.strategies import valid_plans

if TYPE_CHECKING:
    from red_thread_core.documents import Document, Section
    from red_thread_plans.domain import PlanDraft
    from red_thread_plans.nodes import TicketNode, TicketStatus

PAGE = 1
DOCS = 2
RISK = Risk(
    id='R1',
    risk='The glob may miss a path.',
    signal='A collision is stored.',
    handling=Mitigate(ticket='plan-record', criterion='a property pins it'),
    tickets=('plan-record',),
)
INTERFACE = Interface(language='python', source='def draw(plan): ...')


@dataclass(slots=True, kw_only=True, frozen=True)
class Revised:
    name: str
    draft: PlanDraft
    statuses: dict[str, TicketStatus]
    marks: tuple[pytest.MarkDecorator, ...] = ()


def ticket_revision_cases() -> pytest.MarkDecorator:
    draft = create_valid_draft()
    docs = draft.tickets[DOCS]
    record = draft.tickets[0]
    retitled = Revised(
        name='retitled',
        draft=replace_ticket(draft, DOCS, replace(docs, title='write the docs again')),
        statuses={'plan-record': 'unchanged', 'plan-page': 'unchanged', 'docs': 'changed'},
    )
    regrounded = Revised(
        name='regrounded',
        draft=replace_ticket(draft, 0, replace(record, acceptance=record.acceptance[:0])),
        statuses={'plan-record': 'changed', 'plan-page': 'unchanged', 'docs': 'unchanged'},
    )
    added = Revised(
        name='added',
        draft=add_tickets(draft, create_ticket_draft('web-page', 'web', ('web/*.html',))),
        statuses={
            'plan-record': 'unchanged',
            'plan-page': 'unchanged',
            'docs': 'unchanged',
            'web-page': 'new',
        },
    )
    return pytest.mark.parametrize('case', as_params((retitled, regrounded, added)))


def list_titles(document: Document) -> list[str]:
    return [section.title for section in (*document.sections, *document.appendix)]


def find_section(document: Document, title: str) -> Section:
    sections = (*document.sections, *document.appendix)
    return next(section for section in sections if section.title == title)


def list_section_tickets(section: Section) -> tuple[TicketNode, ...]:
    lists = (block.tickets for block in section.blocks if isinstance(block, TicketList))
    return tuple(chain.from_iterable(lists))


def read_marks(document: Document) -> dict[str, TicketStatus]:
    return {ticket.id: ticket.status for ticket in list_tickets(document)}


def read_facts(document: Document) -> dict[str, str]:
    return {fact.label: fact.value for fact in list_facts(render_page(document))}


class TestMarks:
    first = stamp_plan(create_valid_draft())

    @ticket_revision_cases()
    def test_each_ticket_is_marked_by_how_it_differs_from_the_revision_before(
        self, case: Revised
    ) -> None:
        document = create_plan_document(stamp_plan(case.draft, 2), self.first)

        assert read_marks(document) == case.statuses

    def test_a_ticket_left_out_is_listed_under_a_folded_dropped_section(self) -> None:
        draft = replace(create_valid_draft(), tickets=create_valid_draft().tickets[:DOCS])

        document = create_plan_document(stamp_plan(draft, 2), self.first)

        assert find_section(document, 'Dropped').folded
        assert '- docs: build docs' in render_markdown(document).splitlines()
        changes = read_facts(document)['Changes']
        assert changes == 'since revision 1: 0 new, 0 changed, 2 unchanged, 1 dropped'

    def test_the_first_revision_says_so_and_drops_nothing(self) -> None:
        document = create_plan_document(self.first)

        facts = read_facts(document)
        assert (facts['Revision'], facts['Changes']) == ('1', 'first revision')
        assert facts['Tickets'] == '3 in 2 worktrees'
        assert 'Dropped' not in list_titles(document)


class TestMarkProperties:
    @given(draft=valid_plans)
    def test_each_ticket_is_shown_once_in_its_worktree_in_stack_order(
        self, draft: PlanDraft
    ) -> None:
        plan = stamp_plan(draft)

        document = create_plan_document(plan)

        for worktree in plan.worktrees:
            shown = list_section_tickets(find_section(document, f'Worktree {worktree}'))
            assert [ticket.id for ticket in shown] == [ticket.id for ticket in plan.stack(worktree)]
        assert len(list_tickets(document)) == len(plan.tickets)

    @given(draft=valid_plans)
    def test_without_a_revision_before_every_ticket_is_new(self, draft: PlanDraft) -> None:
        document = create_plan_document(stamp_plan(draft))

        assert set(read_marks(document).values()) == {'new'}

    @given(draft=valid_plans)
    def test_against_the_same_plan_every_ticket_is_unchanged_and_none_dropped(
        self, draft: PlanDraft
    ) -> None:
        document = create_plan_document(stamp_plan(draft, 2), stamp_plan(draft))

        assert set(read_marks(document).values()) == {'unchanged'}
        assert 'Dropped' not in list_titles(document)


class TestLayout:
    draft = create_valid_draft()

    def test_the_plan_comes_first_then_a_section_per_worktree_then_the_chart(self) -> None:
        document = create_plan_document(stamp_plan(self.draft))

        assert list_titles(document) == [
            'Approach',
            'Invariants',
            'Non-goals',
            'Worktree core',
            'Worktree docs',
            'Worktrees',
        ]

    def test_a_risk_is_a_point_naming_its_handling_and_its_signal(self) -> None:
        document = create_plan_document(stamp_plan(replace(self.draft, risks=(RISK,))))

        assert list_titles(document)[-2:] == ['Risks', 'Worktrees']
        assert (
            '- R1, mitigated by ticket plan-record (a property pins it): The glob may miss a path.'
            ' Signal: A collision is stored. Touches plan-record.'
        ) in render_markdown(document).splitlines()

    def test_an_interface_is_a_listing_on_its_ticket(self) -> None:
        page = replace(self.draft.tickets[PAGE], interface=INTERFACE)

        document = create_plan_document(stamp_plan(replace_ticket(self.draft, PAGE, page)))

        listings = {ticket.id: ticket.interface for ticket in list_tickets(document)}
        assert listings['plan-page'] == CodeListing(language='python', source=INTERFACE.source)
        assert listings['docs'] is None

    def test_the_chart_draws_each_worktree_and_an_arrow_from_each_dependency(self) -> None:
        document = create_plan_document(stamp_plan(self.draft))

        (chart,) = find_section(document, 'Worktrees').blocks
        assert isinstance(chart, Flowchart)
        lines = chart.lines
        assert [line for line in lines if 'subgraph' in line] == [
            '  subgraph l0["core"]',
            '  subgraph l1["docs"]',
        ]
        assert [line for line in lines if '-->' in line] == ['  n0 --> n1']
        assert '    n2["docs: build docs"]:::s_new' in lines

    def test_the_toolbar_counts_the_tickets_by_worktree_and_by_status(self) -> None:
        docs = replace(self.draft.tickets[DOCS], title='write the docs again')
        revised = stamp_plan(replace_ticket(self.draft, DOCS, docs), 2)

        page = render_plan_page(create_plan_document(revised, stamp_plan(self.draft)))

        chips = chain.from_iterable(list_chip_groups(page))
        assert [(chip.group, chip.value, chip.count) for chip in chips] == [
            ('worktree', 'core', 2),
            ('worktree', 'docs', 1),
            ('status', 'changed', 1),
            ('status', 'unchanged', 2),
        ]
