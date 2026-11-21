# /// script
# requires-python = ">=3.14"
# ///
"""PreToolUse hook on the Agent tool: refuses a red-thread agent's dispatch outside its roster.

The primary, which is the session, may dispatch every agent. A lead may dispatch the scouts. A
scout and the skeptic dispatch nobody. A dispatch of an agent that is not red-thread's, or by a
caller that is not red-thread's, is left alone. On input it cannot read, the hook allows.
"""

import json
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

PREFIX = 'red-thread:'
SCOUTS = ('code-sense', 'code-lens', 'web-head', 'research-cell')

type Teams = Mapping[str, tuple[str, ...]]


def create_teams() -> dict[str, tuple[str, ...]]:
    return {
        'research-lead': SCOUTS,
        'code-sense': (),
        'code-lens': (),
        'web-head': (),
        'research-cell': (),
        'peer-review': (),
    }


def name_agent(name: str) -> str:
    return f'{PREFIX}{name}'


@dataclass(slots=True, kw_only=True, frozen=True)
class Dispatch:
    caller: str | None
    callee: str | None


@dataclass(slots=True, kw_only=True, frozen=True)
class Refusal:
    caller: str
    callee: str
    team: tuple[str, ...]

    @property
    def reason(self) -> str:
        refused = f'so the dispatch of {name_agent(self.callee)} was refused'
        advice = 'If the work needs that agent, say so in your report and let your caller decide.'
        if not self.team:
            return f'{name_agent(self.caller)} dispatches no agents, {refused}. {advice}'

        allowed = ', '.join(map(name_agent, self.team))
        return f'{name_agent(self.caller)} may dispatch only {allowed}, {refused}. {advice}'


@dataclass(slots=True, kw_only=True, frozen=True)
class RosterPolicy:
    dispatch: Dispatch
    teams: Teams = field(default_factory=create_teams)

    @property
    def caller(self) -> str | None:
        name = (self.dispatch.caller or '').removeprefix(PREFIX)
        if name in self.teams:
            return name

        return None

    @property
    def callee(self) -> str | None:
        named = self.dispatch.callee or ''
        if named.startswith(PREFIX):
            return named.removeprefix(PREFIX)

        return None

    def get_dispatch_problem(self) -> Refusal | None:
        caller = self.caller
        callee = self.callee
        if caller is None or callee is None:
            return None

        team = self.teams[caller]
        if callee in team:
            return None

        return Refusal(caller=caller, callee=callee, team=team)


def read_text(record: object, key: str) -> str | None:
    if not isinstance(record, dict):
        return None

    value = record.get(key)
    if isinstance(value, str):
        return value

    return None


def read_dispatch(payload: object) -> Dispatch:
    tool_input = payload.get('tool_input') if isinstance(payload, dict) else None
    return Dispatch(
        caller=read_text(payload, 'agent_type'),
        callee=read_text(tool_input, 'subagent_type'),
    )


def read_payload(text: str) -> object:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def describe_denial(refusal: Refusal) -> str:
    decision = {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': refusal.reason,
    }
    return json.dumps({'hookSpecificOutput': decision})


def main() -> int:
    policy = RosterPolicy(dispatch=read_dispatch(read_payload(sys.stdin.read())))
    if refusal := policy.get_dispatch_problem():
        print(describe_denial(refusal))

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
