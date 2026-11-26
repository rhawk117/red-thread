"""A ticket and a code listing, as the page and as Markdown write them."""

from dataclasses import replace
from html import escape
from typing import TYPE_CHECKING

import pytest
from red_thread_core.documents import CodeListing, Document, Section
from red_thread_plans.nodes import TicketList

from tests.casefile.pages.builders import payload_params
from tests.casefile.pages.html_reading import find_tags, list_code_spans, list_item_refs, list_spans
from tests.casefile.writers.reading import render_markdown, render_page
from tests.plans.page.builders import create_ticket_node

if TYPE_CHECKING:
    from red_thread_core.documents import Block
    from red_thread_plans.nodes import TicketNode


def payload_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('payload', payload_params())


def create_worktree_document(*blocks: Block) -> Document:
    return Document(title='A plan', sections=(Section(title='Worktree core', blocks=blocks),))


def render_tickets(*tickets: TicketNode) -> str:
    return render_page(create_worktree_document(TicketList(tickets=tickets)))


class TestTicketMarkup:
    def test_a_ticket_is_an_entry_marked_with_its_worktree_and_status(self) -> None:
        page = render_tickets(create_ticket_node())

        tickets = [item for item in find_tags(page, 'li') if 'data-worktree' in item]
        assert tickets == [
            {'class': 'entry ticket', 'data-worktree': 'core', 'data-status': 'changed'}
        ]
        assert list_item_refs(page) == ['plan-page']

    def test_the_status_is_a_badge_before_the_title(self) -> None:
        (status,) = list_spans(render_tickets(create_ticket_node()), 'status')

        assert (status.attributes['data-status'], status.body) == ('changed', 'changed')

    def test_the_why_follows_the_title(self) -> None:
        page = render_tickets(create_ticket_node())

        assert '<p class="why">Why: the owner reads the plan in a browser</p>' in page

    def test_each_criterion_names_the_entries_that_require_it(self) -> None:
        page = render_tickets(create_ticket_node())

        assert '<li>the page renders <span class="required">required by e1, e2</span></li>' in page

    def test_the_place_the_dependencies_and_the_owned_paths_are_notes(self) -> None:
        page = render_tickets(create_ticket_node())

        assert '<li class="stamp">worktree core, position 2</li>' in page
        assert '<li>depends on: plan-record</li>' in page
        assert list_code_spans(page) == ['plan', 'core/pages/*.py', 'draw(plan) -> Path']

    def test_the_interface_is_a_listing_tagged_with_its_language(self) -> None:
        page = render_tickets(create_ticket_node())

        listing = (
            '<pre class="listing" data-language="python"><code>draw(plan) -&gt; Path</code></pre>'
        )
        assert listing in page

    def test_a_ticket_without_an_interface_has_no_listing(self) -> None:
        page = render_tickets(replace(create_ticket_node(), interface=None))

        assert 'class="listing"' not in page

    def test_an_empty_ticket_list_writes_nothing(self) -> None:
        assert '<ol class="thread">' not in render_tickets()

    @payload_cases()
    def test_a_title_and_an_interface_are_escaped(self, payload: str) -> None:
        page = render_tickets(create_ticket_node(title=payload, source=payload))

        assert payload not in page
        assert escape(payload) in page


class TestTicketMarkdown:
    def test_a_ticket_is_its_title_status_and_place_then_its_promises(self) -> None:
        lines = render_markdown(
            create_worktree_document(TicketList(tickets=(create_ticket_node(),)))
        )

        assert lines.splitlines()[-3:] == [
            '- draw the `plan` (changed; worktree core, position 2) [plan-page]',
            '  Why: the owner reads the plan in a browser',
            '  - the page renders (required by e1, e2)',
        ]

    def test_a_listing_is_a_fenced_block_tagged_with_its_language(self) -> None:
        listing = CodeListing(language='go', source='func A()\nfunc B()')

        lines = render_markdown(create_worktree_document(listing)).splitlines()

        assert lines[-4:] == ['```go', 'func A()', 'func B()', '```']
