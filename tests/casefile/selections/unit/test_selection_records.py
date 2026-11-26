"""load_selection and SelectionRecord: what a selection file may hold and what it becomes."""

from dataclasses import dataclass

import pytest
from red_thread_casefile.errors import MalformedSelectionError
from red_thread_casefile.lenses import Selection
from red_thread_casefile.schemas import SelectionRecord, load_selection

from tests.params import as_params


@dataclass(slots=True, kw_only=True, frozen=True)
class MalformedSelection:
    name: str
    text: str
    reason_names: str
    marks: tuple[pytest.MarkDecorator, ...] = ()


def malformed_selection_cases() -> pytest.MarkDecorator:
    scenarios = [
        MalformedSelection(name='not-json', text='title: brief', reason_names='it is not JSON ('),
        MalformedSelection(
            name='truncated-json', text='{"title": "a"', reason_names='it is not JSON ('
        ),
        MalformedSelection(name='json-array', text='["e1"]', reason_names='not a JSON object'),
        MalformedSelection(name='json-string', text='"e1"', reason_names='not a JSON object'),
        MalformedSelection(name='json-number', text='3', reason_names='not a JSON object'),
        MalformedSelection(name='json-null', text='null', reason_names='not a JSON object'),
        MalformedSelection(name='unknown-key', text='{"mood": "calm"}', reason_names='mood'),
        MalformedSelection(
            name='known-key-beside-unknown', text='{"title": "a", "ref": []}', reason_names='ref'
        ),
        MalformedSelection(name='title-not-a-string', text='{"title": 5}', reason_names='title'),
        MalformedSelection(name='goal-not-a-string', text='{"goal": ["a"]}', reason_names='goal'),
        MalformedSelection(name='title-null', text='{"title": null}', reason_names='title'),
        MalformedSelection(
            name='include-a-bare-string', text='{"include": "e1"}', reason_names='include'
        ),
        MalformedSelection(
            name='include-holds-a-number', text='{"include": ["e1", 2]}', reason_names='include'
        ),
        MalformedSelection(name='include-null', text='{"include": null}', reason_names='include'),
        MalformedSelection(
            name='blocking-an-object', text='{"blocking": {"e1": true}}', reason_names='blocking'
        ),
        MalformedSelection(
            name='blocking-holds-null', text='{"blocking": [null]}', reason_names='blocking'
        ),
    ]
    return pytest.mark.parametrize('scenario', as_params(scenarios))


def find_selection_problem(text: str) -> MalformedSelectionError | None:
    loaded = load_selection(text)
    if isinstance(loaded, MalformedSelectionError):
        return loaded

    return loaded.get_shape_problem()


def read_selection(text: str) -> Selection:
    loaded = load_selection(text)
    assert isinstance(loaded, SelectionRecord)
    return loaded.parse()


class TestMalformedSelections:
    @malformed_selection_cases()
    def test_a_selection_that_is_not_one_object_of_known_typed_keys_is_malformed(
        self, scenario: MalformedSelection
    ) -> None:
        problem = find_selection_problem(scenario.text)

        assert isinstance(problem, MalformedSelectionError)
        assert scenario.reason_names in problem.reason


class TestUsableSelections:
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
    def test_selection_has_no_problem(self, text: str) -> None:
        assert not find_selection_problem(text)

    def test_empty_or_blank_text_is_the_empty_selection(self) -> None:
        assert read_selection('') == Selection()
        assert read_selection('   \n') == Selection()
        assert read_selection('{}') == Selection()

    def test_every_key_is_read_into_the_selection(self) -> None:
        selection = read_selection(
            '{"title": " T ", "goal": "G", "include": ["e2", "e1"], "blocking": ["e1"]}'
        )

        assert selection == Selection(title='T', goal='G', include=('e2', 'e1'), blocking=('e1',))

    def test_an_absent_list_is_not_the_same_as_an_empty_list(self) -> None:
        assert read_selection('{}').blocking is None
        assert read_selection('{"blocking": []}').blocking == ()
        assert read_selection('{}').include is None
        assert read_selection('{"include": []}').include == ()

    def test_include_keeps_the_order_it_was_written_in(self) -> None:
        selection = read_selection('{"include": ["e9", "e2", "T1.e1"]}')

        assert selection.include == ('e9', 'e2', 'T1.e1')
