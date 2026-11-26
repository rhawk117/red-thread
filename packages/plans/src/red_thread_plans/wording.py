"""The plan's words as the page shows them: one line of text, a risk and its handling."""

from typing import TYPE_CHECKING

from red_thread_core.documents import parse_line
from red_thread_core.util import squeeze

from red_thread_plans.domain import Mitigate, YouIntervene

if TYPE_CHECKING:
    from red_thread_core.documents import Line

    from red_thread_plans.domain import Acceptance, Handling, Risk


def to_line(text: str) -> Line:
    return parse_line(squeeze(text))


def describe_handling(handling: Handling) -> str:
    if isinstance(handling, Mitigate):
        criterion = '' if handling.criterion is None else f' ({handling.criterion})'
        return f'mitigated by ticket {handling.ticket}{criterion}'

    if isinstance(handling, YouIntervene):
        return f'you intervene, and {", ".join(handling.recut)} would be cut again'

    return 'accepted'


def describe_risk(risk: Risk) -> str:
    touched = ', '.join(risk.tickets) or 'no ticket'
    handled = describe_handling(risk.handling)
    return f'{risk.id}, {handled}: {risk.risk} Signal: {risk.signal} Touches {touched}.'


def describe_criterion(acceptance: Acceptance) -> str:
    return f'{acceptance.criterion} (required by {", ".join(acceptance.required_by)})'
