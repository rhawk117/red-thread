"""Drives red_thread_plans.cli.main in-process beside the case file command line."""

import io
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from red_thread_plans.cli import main

from tests.casefile.commands.cli import CliRun

if TYPE_CHECKING:
    import pytest


@dataclass(slots=True, kw_only=True, frozen=True)
class PlanHarness:
    scratch: Path
    capsys: pytest.CaptureFixture[str]
    monkeypatch: pytest.MonkeyPatch

    @property
    def plan_file(self) -> Path:
        return self.scratch.joinpath('plan.json')

    def run(self, *argv: str, stdin: str | None = None) -> CliRun:
        if stdin is not None:
            self.monkeypatch.setattr(sys, 'stdin', io.StringIO(stdin))
        code = main(list(argv))
        captured = self.capsys.readouterr()
        return CliRun(code=code, out=captured.out, err=captured.err)

    def init(self, root: Path, title: str = 'give a case a plan') -> Path:
        result = self.run('init', '--root', str(root), '--title', title)
        assert result.code == 0, result.err
        return Path(result.out.splitlines()[0].removeprefix('created '))

    def revise(self, plan: Path, text: str) -> CliRun:
        return self.run('revise', '--plan', str(plan), stdin=text)

    def revise_from_file(self, plan: Path, text: str) -> CliRun:
        self.plan_file.write_text(text, encoding='utf-8')
        return self.run('revise', '--plan', str(plan), '--file', str(self.plan_file))

    def render(self, plan: Path) -> CliRun:
        return self.run('render', '--plan', str(plan))
