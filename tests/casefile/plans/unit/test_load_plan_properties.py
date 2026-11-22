"""load_plan: any text is a plan object, an empty plan or a malformed plan, never an error."""

import msgspec
from hypothesis import example, given
from hypothesis import strategies as st
from red_thread_casefile.errors import MalformedPlanError
from red_thread_casefile.schemas import PlanRecord, load_plan

NOT_AN_OBJECT = 'it is not a JSON object'
scalars = st.one_of(st.none(), st.booleans(), st.integers(), st.text(max_size=20))
json_values = st.recursive(scalars, st.lists, max_leaves=8)
json_objects = st.dictionaries(st.text(max_size=10), json_values, max_size=5)
non_objects = st.one_of(scalars, st.lists(json_values, max_size=4))


def encode(value: object) -> str:
    return msgspec.json.encode(value).decode()


@given(text=st.text())
@example(text='')
@example(text='{')
@example(text='[1, 2')
@example(text='\x00')
def test_no_text_makes_load_plan_raise(text: str) -> None:
    assert isinstance(load_plan(text), PlanRecord | MalformedPlanError)


@given(text=st.text(alphabet=' \t\r\n\x0b\x0c\x85\N{LINE SEPARATOR}', max_size=8))
def test_a_blank_text_is_the_empty_plan(text: str) -> None:
    assert load_plan(text) == PlanRecord(record={})


@given(value=json_objects)
def test_a_json_object_becomes_the_plan_record_holding_it(value: dict[str, object]) -> None:
    assert load_plan(encode(value)) == PlanRecord(record=value)


@given(value=non_objects)
def test_json_that_is_not_an_object_is_malformed(value: object) -> None:
    outcome = load_plan(encode(value))

    assert isinstance(outcome, MalformedPlanError)
    assert outcome.reason == NOT_AN_OBJECT


@given(rest=st.text(max_size=20))
def test_text_that_is_not_json_is_malformed_with_the_decoder_message(rest: str) -> None:
    outcome = load_plan(f'<{rest}')

    assert isinstance(outcome, MalformedPlanError)
    assert outcome.reason.startswith('it is not JSON (')
