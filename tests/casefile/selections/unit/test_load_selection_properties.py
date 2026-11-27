"""load_selection: any text is a selection, an empty one or a malformed one, never an error."""

from hypothesis import example, given
from hypothesis import strategies as st
from red_thread_casefile.errors import MalformedSelectionError
from red_thread_casefile.schemas import SelectionRecord, load_selection

from tests.codec import JSON

NOT_AN_OBJECT = 'it is not a JSON object'
scalars = st.one_of(st.none(), st.booleans(), st.integers(), st.text(max_size=20))
json_values = st.recursive(scalars, st.lists, max_leaves=8)
json_objects = st.dictionaries(st.text(max_size=10), json_values, max_size=5)
non_objects = st.one_of(scalars, st.lists(json_values, max_size=4))


def encode(value: object) -> str:
    return JSON.encode_text(value)


@given(text=st.text())
@example(text='')
@example(text='{')
@example(text='[1, 2')
@example(text='\x00')
def test_no_text_makes_load_selection_raise(text: str) -> None:
    assert isinstance(load_selection(JSON, text), SelectionRecord | MalformedSelectionError)


@given(text=st.text(alphabet=' \t\r\n\x0b\x0c\x85\N{LINE SEPARATOR}', max_size=8))
def test_a_blank_text_is_the_empty_selection(text: str) -> None:
    assert load_selection(JSON, text) == SelectionRecord(record={})


@given(value=json_objects)
def test_a_json_object_becomes_the_selection_record_holding_it(value: dict[str, object]) -> None:
    assert load_selection(JSON, encode(value)) == SelectionRecord(record=value)


@given(value=non_objects)
def test_json_that_is_not_an_object_is_malformed(value: object) -> None:
    outcome = load_selection(JSON, encode(value))

    assert isinstance(outcome, MalformedSelectionError)
    assert outcome.reason == NOT_AN_OBJECT


@given(rest=st.text(max_size=20))
def test_text_that_is_not_json_is_malformed_with_the_decoder_message(rest: str) -> None:
    outcome = load_selection(JSON, f'<{rest}')

    assert isinstance(outcome, MalformedSelectionError)
    assert outcome.reason.startswith('it is not JSON (')
