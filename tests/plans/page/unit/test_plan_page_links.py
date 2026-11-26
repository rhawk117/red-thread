"""PlanPage: the entries behind each criterion, the links out and what changed since the last."""

from msgspec.structs import replace
from red_thread_core.places import link_board
from red_thread_core.writers.markdown import write_markdown_line
from red_thread_plans.changes import PlanChanges
from red_thread_plans.domain import CaseRecord, IssueLink
from red_thread_plans.filters import list_tickets
from red_thread_plans.nodes import ChangeList, FieldChange
from red_thread_plans.page import PlanPage
from red_thread_plans.terms import PLAN_TERMS

from tests.casefile.ledger.builders import CASE_ID, create_case
from tests.casefile.pages.html_reading import list_facts
from tests.casefile.writers.reading import render_markdown, render_page
from tests.plans.revisions.builders import (
    ALIAS,
    PLAN_INDEX,
    create_plan_document,
    create_resting_ledger,
    create_valid_draft,
    replace_ticket,
    stamp_plan,
)

ISSUE_URL = 'https://example.invalid/issues/7'
EPIC_URL = 'https://example.invalid/issues/1'
DOCS = 2


def draw(changes: PlanChanges, *, epic: str | None = None, found: bool = True) -> PlanPage:
    record = CaseRecord(case=create_case(), ledger=create_resting_ledger())
    index = replace(PLAN_INDEX, epic=epic, issues=(IssueLink(ticket='docs', url=ISSUE_URL),))
    return PlanPage(index=index, records={ALIAS: record} if found else {}, changes=changes)


def read_facts(page: PlanPage) -> dict[str, str]:
    return {fact.label: fact.value for fact in list_facts(render_page(page.compose()))}


class TestGrounds:
    first = PlanChanges(plan=stamp_plan(create_valid_draft()))

    def test_each_criterion_shows_the_kind_text_and_board_of_each_entry_behind_it(self) -> None:
        ticket = list_tickets(draw(self.first).compose())[0]

        grounds = ticket.acceptance[0].grounds
        assert [(ground.ref, ground.kind, ground.url) for ground in grounds] == [
            ('C1.e1', 'decision', link_board(CASE_ID, 'e1')),
            ('C1.e2', 'known', link_board(CASE_ID, 'e2')),
        ]
        assert [write_markdown_line(ground.claim) for ground in grounds] == [
            'keep one writer',
            'the store is append only',
        ]

    def test_an_entry_whose_case_is_gone_is_shown_as_missing_without_a_link(self) -> None:
        ticket = list_tickets(draw(self.first, found=False).compose())[0]

        assert {(ground.kind, ground.url) for ground in ticket.acceptance[0].grounds} == {
            (None, None)
        }


class TestLinksOut:
    first = PlanChanges(plan=stamp_plan(create_valid_draft()))

    def test_each_case_links_to_its_board_beside_the_plan(self) -> None:
        text = render_markdown(draw(self.first).compose())

        board = link_board(CASE_ID)
        assert f'- C1: [{CASE_ID}]({board}), {create_case().target}' in text.splitlines()

    def test_the_epic_reads_not_published_until_the_index_records_it(self) -> None:
        assert read_facts(draw(self.first))['Epic'] == 'not published yet'
        assert read_facts(draw(self.first, epic=EPIC_URL))['Epic'] == 'epic'

    def test_a_ticket_carries_its_issue_once_the_index_records_one(self) -> None:
        issues = {ticket.id: ticket.issue for ticket in list_tickets(draw(self.first).compose())}

        assert issues == {'plan-record': None, 'plan-page': None, 'docs': ISSUE_URL}


class TestWhatChanged:
    draft = create_valid_draft()
    first = stamp_plan(draft)

    def revise(self) -> PlanChanges:
        docs = replace(self.draft.tickets[DOCS], title='write the docs again')
        second = replace(replace_ticket(self.draft, DOCS, docs), approach='keep it in core')
        return PlanChanges(plan=stamp_plan(second, 2), previous=self.first)

    def test_the_first_revision_has_no_what_changed_section(self) -> None:
        titles = [section.title for section in create_plan_document(self.first).sections]

        assert 'What changed' not in titles

    def test_a_later_revision_opens_with_what_changed_in_the_plan_and_its_tickets(self) -> None:
        section = draw(self.revise()).compose().sections[0]

        assert section.title == 'What changed'
        assert '- Changed tickets: docs.' in render_markdown(draw(self.revise()).compose())
        fields = next(block for block in section.blocks if isinstance(block, ChangeList))
        assert fields.changes == (
            FieldChange(
                field='approach',
                removed=('store it beside the ledger',),
                added=('keep it in core',),
            ),
        )

    def test_a_changed_ticket_lists_each_field_as_it_was_and_as_it_is(self) -> None:
        changes = {
            ticket.id: ticket.changes for ticket in list_tickets(draw(self.revise()).compose())
        }

        assert changes == {
            'plan-record': (),
            'plan-page': (),
            'docs': (
                FieldChange(
                    field='title', removed=('build docs',), added=('write the docs again',)
                ),
            ),
        }


class TestReading:
    document = create_plan_document(stamp_plan(create_valid_draft()))

    def test_each_worktree_is_a_column_and_the_plan_around_them_is_full_width(self) -> None:
        columns = [section.title for section in self.document.sections if section.column]

        assert columns == ['Worktree core', 'Worktree docs']

    def test_the_page_explains_the_words_it_uses(self) -> None:
        words = {term.word for term in self.document.terms}

        assert self.document.terms == PLAN_TERMS
        assert {'Worktree', 'Ref', 'Done when', 'Epic and issue'} <= words
