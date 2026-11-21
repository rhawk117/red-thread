"""Who dispatches whom, and what the roster hook does about it."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet

LEAD = 'red-thread:research-lead'
SKEPTIC = 'red-thread:peer-review'
SCOUTS = ('red-thread:code-sense', 'red-thread:web-head', 'red-thread:research-cell')
SILENT = ('red-thread:code-sense', 'red-thread:web-head', 'red-thread:research-cell', SKEPTIC)


@dataclass(slots=True, kw_only=True, frozen=True)
class Pairing:
    name: str
    caller: str | None
    callee: object
    marks: tuple[pytest.MarkDecorator, ...] = ()

    @property
    def param(self) -> ParameterSet:
        return pytest.param(self, id=self.name, marks=self.marks)


def allowed_pairing_params() -> list[ParameterSet]:
    by_the_lead = [
        Pairing(name=f'lead-to-{scout.partition(":")[2]}', caller=LEAD, callee=scout)
        for scout in SCOUTS
    ]
    by_the_primary = [
        Pairing(name=f'primary-to-{agent.partition(":")[2]}', caller=None, callee=agent)
        for agent in (LEAD, SKEPTIC, *SCOUTS)
    ]
    untouched = [
        Pairing(name='lead-to-an-agent-outside-the-plugin', caller=LEAD, callee='general-purpose'),
        Pairing(name='lead-to-another-plugin', caller=LEAD, callee='other-plugin:peer-review'),
        Pairing(name='lead-to-a-bare-name', caller=LEAD, callee='peer-review'),
        Pairing(name='outside-caller-to-the-lead', caller='general-purpose', callee=LEAD),
        Pairing(
            name='other-plugin-caller-to-a-scout', caller='other:research-lead', callee=SKEPTIC
        ),
    ]
    pairings = (*by_the_lead, *by_the_primary, *untouched)
    return [pairing.param for pairing in pairings]


def refused_pairing_params() -> list[ParameterSet]:
    by_the_lead = [
        Pairing(name='lead-to-another-lead', caller=LEAD, callee=LEAD),
        Pairing(name='lead-to-the-skeptic', caller=LEAD, callee=SKEPTIC),
        Pairing(name='lead-to-an-unknown-plugin-agent', caller=LEAD, callee='red-thread:nobody'),
        Pairing(name='lead-under-its-bare-name', caller='research-lead', callee=SKEPTIC),
    ]
    by_the_silent = [
        Pairing(name=f'{agent.partition(":")[2]}-to-a-scout', caller=agent, callee=SCOUTS[0])
        for agent in SILENT
    ]
    pairings = (*by_the_lead, *by_the_silent)
    return [pairing.param for pairing in pairings]


def unreadable_input_params() -> list[ParameterSet]:
    return [
        pytest.param('', id='empty'),
        pytest.param('not json', id='not-json'),
        pytest.param('[1, 2]', id='a-list'),
        pytest.param('{"agent_type": "red-thread:research-lead"}', id='no-tool-input'),
        pytest.param(
            '{"agent_type": "red-thread:research-lead", "tool_input": "text"}',
            id='tool-input-is-text',
        ),
        pytest.param(
            '{"agent_type": 7, "tool_input": {"subagent_type": ["red-thread:peer-review"]}}',
            id='names-are-not-text',
        ),
    ]
