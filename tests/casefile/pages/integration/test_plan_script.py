"""The page script on a plan page: lane and status chips hide tickets and the lanes they empty."""

from typing import TYPE_CHECKING

import pytest
from msgspec.structs import replace

from tests.casefile.pages.script import ScriptHarness, click_chip
from tests.casefile.plans.builders import (
    create_plan_document,
    create_valid_draft,
    replace_ticket,
    stamp_plan,
)
from tests.casefile.writers.reading import render_page

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.pages.script import PageState

DOCS = 2


@pytest.fixture
def script(node: str, tmp_path: Path) -> ScriptHarness:
    draft = create_valid_draft()
    docs = replace(draft.tickets[DOCS], title='write the docs again')
    revised = stamp_plan(replace_ticket(draft, DOCS, docs), 2)
    page = render_page(create_plan_document(revised, stamp_plan(draft)))
    return ScriptHarness(node=node, workdir=tmp_path, page=page)


def list_hidden_refs(state: PageState) -> list[str]:
    return [entry['ref'] for entry in state['entries'] if entry['hidden']]


def list_hidden_sections(state: PageState) -> list[str]:
    return [section['title'] for section in state['sections'] if section['hidden']]


class TestPlanFilters:
    def test_a_lane_chip_hides_that_lanes_tickets_and_its_section(
        self, script: ScriptHarness
    ) -> None:
        state = script.play(click_chip('lane', 'docs'))

        assert list_hidden_refs(state) == ['docs']
        assert list_hidden_sections(state) == ['Lane docs']

    def test_a_status_chip_hides_the_tickets_with_that_mark(self, script: ScriptHarness) -> None:
        state = script.play(click_chip('status', 'unchanged'))

        assert list_hidden_refs(state) == ['plan-record', 'plan-page']
        assert list_hidden_sections(state) == ['Lane core']

    def test_lane_and_status_chips_add_up(self, script: ScriptHarness) -> None:
        state = script.play(click_chip('lane', 'core'), click_chip('status', 'changed'))

        assert list_hidden_refs(state) == ['plan-record', 'plan-page', 'docs']
        assert list_hidden_sections(state) == ['Lane core', 'Lane docs']

    def test_a_second_click_shows_the_lane_again(self, script: ScriptHarness) -> None:
        state = script.play(click_chip('lane', 'docs'), click_chip('lane', 'docs'))

        assert list_hidden_refs(state) == []
        assert list_hidden_sections(state) == []
