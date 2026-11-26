"""Translation between plan text, the drafted plan and a stored revision."""

import msgspec

from red_thread_plans.domain import Plan, PlanDraft
from red_thread_plans.errors import PlanShapeError


def decode_draft(text: str) -> PlanDraft | PlanShapeError:
    if not text.strip():
        return PlanShapeError(reason='it is empty')
    try:
        return msgspec.json.decode(text, type=PlanDraft)
    except msgspec.ValidationError as error:
        return PlanShapeError(reason=str(error))
    except msgspec.DecodeError as error:
        return PlanShapeError(reason=f'it is not JSON ({error})')


def plan_to_text(plan: Plan) -> str:
    return msgspec.json.format(msgspec.json.encode(plan), indent=2).decode() + '\n'


def plan_from_text(text: str) -> Plan:
    return msgspec.json.decode(text, type=Plan)
