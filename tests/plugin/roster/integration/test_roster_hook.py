"""hooks/roster.py and its wiring in hooks/hooks.json, run as a child process."""

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tests.plugin.roster.cases import (
    LEAD,
    SCOUTS,
    SKEPTIC,
    allowed_pairing_params,
    refused_pairing_params,
    unreadable_input_params,
)
from tests.plugin.roster.hook import create_payload, read_decision

if TYPE_CHECKING:
    from tests.plugin.roster.cases import Pairing
    from tests.plugin.roster.hook import RosterHook

AGENT_FILES = sorted(Path(__file__).parents[4].joinpath('agents').glob('*.md'))


def allowed_pairing_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('pairing', allowed_pairing_params())


def refused_pairing_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('pairing', refused_pairing_params())


def unreadable_input_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('text', unreadable_input_params())


def agent_file_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        'agent', [pytest.param(path.stem, id=path.stem) for path in AGENT_FILES]
    )


class TestRosterHook:
    @allowed_pairing_cases()
    def test_a_dispatch_inside_the_roster_or_outside_the_plugin_is_left_alone(
        self, roster_hook: RosterHook, pairing: Pairing
    ) -> None:
        finished = roster_hook.dispatch(pairing.caller, pairing.callee)

        assert (finished.code, finished.out, finished.err) == (0, '', '')

    @refused_pairing_cases()
    def test_a_dispatch_outside_the_roster_is_denied(
        self, roster_hook: RosterHook, pairing: Pairing
    ) -> None:
        finished = roster_hook.dispatch(pairing.caller, pairing.callee)

        decision = read_decision(finished)
        assert (finished.code, finished.err) == (0, '')
        assert decision['hookEventName'] == 'PreToolUse'
        assert decision['permissionDecision'] == 'deny'
        assert str(pairing.callee) in decision['permissionDecisionReason']

    def test_the_lead_is_told_whom_it_may_dispatch(self, roster_hook: RosterHook) -> None:
        reason = read_decision(roster_hook.dispatch(LEAD, SKEPTIC))['permissionDecisionReason']

        assert all(scout in reason for scout in SCOUTS)
        assert reason.startswith(f'{LEAD} may dispatch only ')

    def test_a_scout_is_told_it_dispatches_nobody(self, roster_hook: RosterHook) -> None:
        reason = read_decision(roster_hook.dispatch(SCOUTS[0], SCOUTS[1]))[
            'permissionDecisionReason'
        ]

        assert reason.startswith(f'{SCOUTS[0]} dispatches no agents')

    @unreadable_input_cases()
    def test_input_the_hook_cannot_read_allows_the_dispatch(
        self, roster_hook: RosterHook, text: str
    ) -> None:
        finished = roster_hook.send(text)

        assert (finished.code, finished.out, finished.err) == (0, '', '')

    @agent_file_cases()
    def test_every_agent_file_has_a_roster(self, roster_hook: RosterHook, agent: str) -> None:
        finished = roster_hook.dispatch(f'red-thread:{agent}', LEAD)

        assert read_decision(finished)['permissionDecision'] == 'deny'


class TestRosterWiring:
    def test_the_hook_runs_before_the_agent_tool_and_nothing_else(
        self, roster_hook: RosterHook
    ) -> None:
        wiring = roster_hook.wiring['hooks']

        assert list(wiring) == ['PreToolUse']
        assert [group['matcher'] for group in wiring['PreToolUse']] == ['Agent']

    def test_the_wired_command_denies_a_dispatch_outside_the_roster(
        self, roster_hook: RosterHook
    ) -> None:
        finished = roster_hook.send_as_wired(json.dumps(create_payload(LEAD, SKEPTIC)))

        assert finished.code == 0
        assert read_decision(finished)['permissionDecision'] == 'deny'

    def test_the_wired_command_leaves_a_dispatch_inside_the_roster_alone(
        self, roster_hook: RosterHook
    ) -> None:
        finished = roster_hook.send_as_wired(json.dumps(create_payload(LEAD, SCOUTS[0])))

        assert (finished.code, finished.out) == (0, '')
