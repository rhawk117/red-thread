"""decode_draft: any text is a draft or one shape fault that names where it is, never an error."""

from dataclasses import dataclass

import msgspec
import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from red_thread_casefile.plans.domain import PlanDraft
from red_thread_casefile.plans.errors import PlanShapeError
from red_thread_casefile.plans.schemas import decode_draft

from tests.casefile.plans.builders import create_valid_draft
from tests.casefile.plans.strategies import valid_plans
from tests.params import as_params


@dataclass(slots=True, kw_only=True, frozen=True)
class ShapeFault:
    name: str
    text: str
    reason: str
    marks: tuple[pytest.MarkDecorator, ...] = ()


def encode(value: object) -> str:
    return msgspec.json.encode(value).decode()


def describe_tickets(tickets: list[dict[str, object]]) -> str:
    return encode({'intent': 'x', 'approach': 'y', 'tickets': tickets})


def plan_shape_fault_cases() -> pytest.MarkDecorator:
    ticket = {'id': 'a', 'title': 'A', 'lane': 'core'}
    risk = {'id': 'R1', 'risk': 'r', 'signal': 's', 'handling': {'kind': 'maybe'}}
    faults = (
        ShapeFault(name='empty', text='  ', reason='it is empty'),
        ShapeFault(name='not-json', text='{"intent": ', reason='it is not JSON'),
        ShapeFault(name='not-an-object', text='[]', reason='Expected `object`'),
        ShapeFault(name='missing-key', text=encode({'intent': 'x'}), reason='approach'),
        ShapeFault(
            name='unknown-key',
            text=encode({'intent': 'x', 'approach': 'y', 'owner': 'me'}),
            reason='owner',
        ),
        ShapeFault(
            name='nested-missing-key',
            text=describe_tickets([{'id': 'a', 'title': 'A'}]),
            reason='$.tickets[0]',
        ),
        ShapeFault(
            name='stamped-field',
            text=describe_tickets([{**ticket, 'position': 1}]),
            reason='position',
        ),
        ShapeFault(
            name='unknown-handling',
            text=encode({'intent': 'x', 'approach': 'y', 'risks': [risk]}),
            reason='$.risks[0].handling',
        ),
    )
    return pytest.mark.parametrize('fault', as_params(faults))


class TestDecodeDraft:
    @given(text=st.text())
    @example(text='')
    @example(text='{')
    @example(text='\x00')
    def test_no_text_makes_decode_draft_raise(self, text: str) -> None:
        assert isinstance(decode_draft(text), PlanDraft | PlanShapeError)

    @given(plan=valid_plans)
    @example(plan=create_valid_draft())
    def test_a_draft_sent_as_json_comes_back_whole(self, plan: PlanDraft) -> None:
        assert decode_draft(encode(plan)) == plan

    @plan_shape_fault_cases()
    def test_a_shape_fault_is_named_where_it_is(self, fault: ShapeFault) -> None:
        decoded = decode_draft(fault.text)

        assert isinstance(decoded, PlanShapeError)
        assert fault.reason in str(decoded)
