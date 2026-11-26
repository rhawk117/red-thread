"""The plans beside the cases, read from each plan's index on disk."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from red_thread_core.mentions import DirectoryMentionShelf, PlanMention

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(slots=True, kw_only=True, frozen=True)
class PlanShelf:
    directory: Path
    shelf: DirectoryMentionShelf

    def put(self, plan_id: str, text: str) -> None:
        home = self.directory.joinpath(plan_id)
        home.mkdir(parents=True)
        home.joinpath('plan.json').write_text(text, encoding='utf-8')


class TestDirectoryMentionShelf:
    @pytest.fixture
    def plans(self, tmp_path: Path) -> PlanShelf:
        directory = tmp_path.joinpath('plans')
        return PlanShelf(directory=directory, shelf=DirectoryMentionShelf(directory=directory))

    def test_each_plan_that_cites_the_case_is_listed_in_id_order(self, plans: PlanShelf) -> None:
        plans.put('b-ship', '{"id": "b-ship", "title": "Ship", "cases": ["c1"]}')
        plans.put('a-cut', '{"id": "a-cut", "title": "Cut", "cases": ["c1", "c2"]}')
        plans.put('c-other', '{"id": "c-other", "title": "Other", "cases": ["c2"]}')

        assert plans.shelf.list_mentions('c1') == (
            PlanMention(id='a-cut', title='Cut', cases=('c1', 'c2')),
            PlanMention(id='b-ship', title='Ship', cases=('c1',)),
        )

    def test_an_unreadable_index_and_a_plan_without_one_are_skipped(self, plans: PlanShelf) -> None:
        plans.put('a-cut', '{"id": "a-cut", "title": "Cut", "cases": ["c1"]}')
        plans.put('b-broken', '{"id": ')
        plans.directory.joinpath('c-empty').mkdir()

        assert [mention.id for mention in plans.shelf.list_mentions('c1')] == ['a-cut']

    def test_no_plans_directory_means_no_mentions(self, plans: PlanShelf) -> None:
        assert plans.shelf.list_mentions('c1') == ()
