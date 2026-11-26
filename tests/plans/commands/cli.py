"""Drives red_thread_plans.cli.main in-process beside the case file command line."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from red_thread_plans.cli import main

from tests.casefile.commands.cli import CliRun
from tests.plans.document.builders import TITLE

if TYPE_CHECKING:
    import pytest


def name_cases(case_ids: tuple[str, ...]) -> list[str]:
    return [token for case_id in case_ids for token in ('--case', case_id)]


@dataclass(slots=True, kw_only=True, frozen=True)
class PlanHarness:
    root: Path
    capsys: pytest.CaptureFixture[str]

    def run(self, *argv: str) -> CliRun:
        code = main(list(argv))
        captured = self.capsys.readouterr()
        return CliRun(code=code, out=captured.out, err=captured.err)

    def init(self, *case_ids: str) -> CliRun:
        return self.run('init', '--root', str(self.root), '--title', TITLE, *name_cases(case_ids))

    def open(self, *case_ids: str) -> Path:
        result = self.init(*case_ids)
        assert result.code == 0, result.err
        return Path(result.out.splitlines()[0].removeprefix('created '))

    def check(self, plan: Path) -> CliRun:
        return self.run('check', '--plan', str(plan))
