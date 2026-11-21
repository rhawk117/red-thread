"""Runs the roster hook as Claude Code does: one JSON payload on standard input."""

import json
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from tests.casefile.launcher.children import ChildRunner

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.launcher.children import Finished

PLUGIN_ROOT = '${CLAUDE_PLUGIN_ROOT}'


def create_payload(caller: str | None, callee: object) -> dict[str, object]:
    payload: dict[str, object] = {
        'hook_event_name': 'PreToolUse',
        'tool_name': 'Agent',
        'tool_input': {'subagent_type': callee, 'prompt': 'look it up'},
    }
    if caller is not None:
        payload['agent_type'] = caller
    return payload


@dataclass(slots=True, kw_only=True, frozen=True)
class RosterHook:
    root: Path

    @property
    def script(self) -> Path:
        return self.root.joinpath('hooks', 'roster.py')

    @property
    def wiring(self) -> dict[str, Any]:
        text = self.root.joinpath('hooks', 'hooks.json').read_text(encoding='utf-8')
        wiring: dict[str, Any] = json.loads(text)
        return wiring

    @property
    def wired_command(self) -> tuple[str, ...]:
        (group,) = self.wiring['hooks']['PreToolUse']
        (hook,) = group['hooks']
        arguments = (argument.replace(PLUGIN_ROOT, str(self.root)) for argument in hook['args'])
        return (hook['command'], *arguments)

    def send(self, text: str) -> Finished:
        return ChildRunner(cwd=self.root).run(sys.executable, str(self.script), stdin=text)

    def send_as_wired(self, text: str) -> Finished:
        return ChildRunner(cwd=self.root).run(*self.wired_command, stdin=text)

    def dispatch(self, caller: str | None, callee: object) -> Finished:
        return self.send(json.dumps(create_payload(caller, callee)))


def read_decision(finished: Finished) -> dict[str, str]:
    decision: dict[str, str] = json.loads(finished.out)['hookSpecificOutput']
    return decision
