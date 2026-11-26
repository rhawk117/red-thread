"""Drives red_thread_plans.cli.main in-process beside the case file command line."""

import io
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_plans.cli import main

from tests.casefile.commands.cli import CliRun

if TYPE_CHECKING:
    from pathlib import Path

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

    def revise(self, case: Path, text: str) -> CliRun:
        return self.run('revise', '--case', str(case), stdin=text)

    def revise_from_file(self, case: Path, text: str) -> CliRun:
        self.plan_file.write_text(text, encoding='utf-8')
        return self.run('revise', '--case', str(case), '--file', str(self.plan_file))
