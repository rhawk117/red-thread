"""A plan's index read as a mention of the cases it cites, and a shelf of mentions."""

import json

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_core.mentions import MemoryMentionShelf, PlanMention, read_mention


def unreadable_index_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        'text',
        [
            pytest.param('not json', id='not-json'),
            pytest.param('[]', id='not-an-object'),
            pytest.param('{"title": "t"}', id='no-id'),
            pytest.param('{"id": 1, "title": "t"}', id='id-not-text'),
            pytest.param('{"id": "p"}', id='no-title'),
            pytest.param('{"id": "p", "title": "t", "cases": [1]}', id='case-not-text'),
            pytest.param('{"id": "p", "title": "t", "cases": "c1"}', id='cases-not-a-list'),
        ],
    )


class TestReadMention:
    @given(plan_id=st.text(), title=st.text(), cases=st.lists(st.text()))
    def test_an_index_reads_back_as_its_id_title_and_cases(
        self, plan_id: str, title: str, cases: list[str]
    ) -> None:
        text = json.dumps({'id': plan_id, 'title': title, 'at': 'now', 'cases': cases})

        assert read_mention(text) == PlanMention(id=plan_id, title=title, cases=tuple(cases))

    def test_an_index_that_cites_no_case_yet_mentions_none(self) -> None:
        assert read_mention('{"id": "p", "title": "t"}') == PlanMention(id='p', title='t', cases=())

    @unreadable_index_cases()
    def test_an_unreadable_index_is_no_mention(self, text: str) -> None:
        assert read_mention(text) is None


class TestMemoryMentionShelf:
    cut = PlanMention(id='cut', title='Cut the work', cases=('c1', 'c2'))
    ship = PlanMention(id='ship', title='Ship it', cases=('c2',))

    def test_a_case_is_mentioned_only_by_the_plans_that_cite_it(self) -> None:
        shelf = MemoryMentionShelf(mentions=(self.cut, self.ship))

        assert shelf.list_mentions('c1') == (self.cut,)
        assert shelf.list_mentions('c2') == (self.cut, self.ship)
        assert shelf.list_mentions('c3') == ()
