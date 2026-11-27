"""Runs the script of a rendered page under ElementChild, against the fake DOM in dom_harness.js."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tests.casefile.launcher.children import ChildRunner
from tests.codec import JSON, decode_json

HARNESS = Path(__file__).with_name('dom_harness.js')

type Step = dict[str, object]
type PageState = dict[str, Any]


def load() -> Step:
    return {'do': 'load'}


def click(select: str, index: int = 0) -> Step:
    return {'do': 'click', 'select': select, 'index': index}


def click_chip(group: str, value: str) -> Step:
    return click(f'[data-filter="{group}"][data-value="{value}"]')


def toggle(index: int, *, opened: bool) -> Step:
    return {'do': 'toggle', 'select': 'details.section', 'index': index, 'open': opened}


def choose_theme(value: str | None) -> Step:
    return {'do': 'theme', 'value': value}


def switch_scheme(*, dark: bool) -> Step:
    return {'do': 'scheme', 'dark': dark}


def navigate(anchor: str) -> Step:
    return {'do': 'navigate', 'id': anchor}


def run_timers() -> Step:
    return {'do': 'timers'}


def deny_clipboard() -> Step:
    return {'do': 'deny_clipboard'}


@dataclass(slots=True, kw_only=True, frozen=True)
class ScriptHarness:
    node: str
    workdir: Path
    page: str

    def play(self, *steps: Step, mermaid: bool = True) -> PageState:
        page_file = self.workdir.joinpath('page.html')
        steps_file = self.workdir.joinpath('steps.json')
        page_file.write_text(self.page, encoding='utf-8')
        steps_file.write_text(
            JSON.encode_text({'steps': steps, 'mermaid': mermaid}), encoding='utf-8'
        )
        runner = ChildRunner(cwd=self.workdir)
        finished = runner.run(self.node, str(HARNESS), str(page_file), str(steps_file))
        assert finished.code == 0, finished.err
        return decode_json(finished.out, dict[str, Any])
