"""load_plan and PlanRecord: what a plan file may hold and what it becomes."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.errors import MalformedPlanError
from red_thread_casefile.lenses import Plan
from red_thread_casefile.schemas import PlanRecord, load_plan

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet


@dataclass(slots=True, kw_only=True, frozen=True)
class MalformedPlan:
    name: str
    text: str
    reason_names: str

    @property
    def param(self) -> ParameterSet:
        return pytest.param(self, id=self.name)


def malformed_plan_cases() -> pytest.MarkDecorator:
    scenarios = [
        MalformedPlan(name='not-json', text='title: brief', reason_names='it is not JSON ('),
        MalformedPlan(name='truncated-json', text='{"title": "a"', reason_names='it is not JSON ('),
        MalformedPlan(name='json-array', text='["e1"]', reason_names='not a JSON object'),
        MalformedPlan(name='json-string', text='"e1"', reason_names='not a JSON object'),
        MalformedPlan(name='json-number', text='3', reason_names='not a JSON object'),
        MalformedPlan(name='json-null', text='null', reason_names='not a JSON object'),
        MalformedPlan(name='unknown-key', text='{"mood": "calm"}', reason_names='mood'),
        MalformedPlan(
            name='known-key-beside-unknown', text='{"title": "a", "ref": []}', reason_names='ref'
        ),
        MalformedPlan(name='title-not-a-string', text='{"title": 5}', reason_names='title'),
        MalformedPlan(name='goal-not-a-string', text='{"goal": ["a"]}', reason_names='goal'),
        MalformedPlan(name='title-null', text='{"title": null}', reason_names='title'),
        MalformedPlan(
            name='include-a-bare-string', text='{"include": "e1"}', reason_names='include'
        ),
        MalformedPlan(
            name='include-holds-a-number', text='{"include": ["e1", 2]}', reason_names='include'
        ),
        MalformedPlan(name='include-null', text='{"include": null}', reason_names='include'),
        MalformedPlan(
            name='blocking-an-object', text='{"blocking": {"e1": true}}', reason_names='blocking'
        ),
        MalformedPlan(
            name='blocking-holds-null', text='{"blocking": [null]}', reason_names='blocking'
        ),
    ]
    return pytest.mark.parametrize('scenario', [scenario.param for scenario in scenarios])


def find_plan_problem(text: str) -> MalformedPlanError | None:
    loaded = load_plan(text)
    if isinstance(loaded, MalformedPlanError):
        return loaded

    return loaded.get_shape_problem()


def read_plan(text: str) -> Plan:
    loaded = load_plan(text)
    assert isinstance(loaded, PlanRecord)
    return loaded.parse()


class TestMalformedPlans:
    @malformed_plan_cases()
    def test_a_plan_that_is_not_one_object_of_known_typed_keys_is_malformed(
        self, scenario: MalformedPlan
    ) -> None:
        problem = find_plan_problem(scenario.text)

        assert isinstance(problem, MalformedPlanError)
        assert scenario.reason_names in problem.reason


class TestUsablePlans:
    @pytest.mark.parametrize(
        'text',
        [
            pytest.param('', id='empty'),
            pytest.param('  \n\t', id='blank'),
            pytest.param('{}', id='empty-object'),
            pytest.param('{"title": "T", "goal": "G"}', id='title-and-goal'),
            pytest.param('{"include": [], "blocking": []}', id='empty-lists'),
            pytest.param('{"include": ["e1", "T1.e2"], "blocking": ["e1"]}', id='refs'),
        ],
    )
    def test_plan_has_no_problem(self, text: str) -> None:
        assert find_plan_problem(text) is None

    def test_empty_or_blank_text_is_the_empty_plan(self) -> None:
        assert read_plan('') == Plan()
        assert read_plan('   \n') == Plan()
        assert read_plan('{}') == Plan()

    def test_every_key_is_read_into_the_plan(self) -> None:
        plan = read_plan(
            '{"title": " T ", "goal": "G", "include": ["e2", "e1"], "blocking": ["e1"]}'
        )

        assert plan == Plan(title='T', goal='G', include=('e2', 'e1'), blocking=('e1',))

    def test_an_absent_list_is_not_the_same_as_an_empty_list(self) -> None:
        assert read_plan('{}').blocking is None
        assert read_plan('{"blocking": []}').blocking == ()
        assert read_plan('{}').include is None
        assert read_plan('{"include": []}').include == ()

    def test_include_keeps_the_order_it_was_written_in(self) -> None:
        plan = read_plan('{"include": ["e9", "e2", "T1.e1"]}')

        assert plan.include == ('e9', 'e2', 'T1.e1')
