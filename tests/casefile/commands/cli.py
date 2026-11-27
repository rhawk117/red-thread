"""Drives red_thread_casefile.cli.main in-process and reports what a caller would see."""

import io
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_casefile.cli import main
from red_thread_casefile.domain import FINDING_HEADING, ROUND_HEADING, RoundStamp
from red_thread_casefile.store import DirectoryCaseRepository

from tests.casefile.findings.blocks import write_findings, write_round
from tests.casefile.ledger.builders import DAY
from tests.casefile.ledger.markdown import SCHEMA, append_text, name_file

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    import pytest
    from red_thread_casefile.domain import Case

    from tests.casefile.ledger.git_repository import GitRepository


def read_file_lines(case: Path, thread: str | None) -> list[str]:
    path = case.joinpath(name_file(thread))
    return path.read_text(encoding='utf-8').splitlines() if path.is_file() else []


def read_case(case: Path) -> Case | None:
    sources = DirectoryCaseRepository(directory=case).read()
    return SCHEMA.read(sources).case


@dataclass(slots=True, kw_only=True, frozen=True)
class CliRun:
    code: int
    out: str
    err: str


@dataclass(slots=True, kw_only=True, frozen=True)
class CliHarness:
    git: GitRepository
    capsys: pytest.CaptureFixture[str]
    monkeypatch: pytest.MonkeyPatch

    @property
    def selection_file(self) -> Path:
        return self.git.root.parent.joinpath('selection.json')

    def run(self, *argv: str, stdin: str | None = None) -> CliRun:
        if stdin is not None:
            self.monkeypatch.setattr(sys, 'stdin', io.StringIO(stdin))
        code = main(list(argv))
        captured = self.capsys.readouterr()
        return CliRun(code=code, out=captured.out, err=captured.err)

    def init(self, target: str = 'why the retry queue stalls', *extra: str) -> Path:
        result = self.run(
            'init',
            '--root',
            str(self.git.root),
            '--target',
            target,
            '--kind',
            'root-cause',
            '--bar',
            'name the line',
            *extra,
        )
        assert result.code == 0, result.err
        created = result.out.splitlines()[0].removeprefix('created ')
        return self.git.root.joinpath(created).resolve()

    def write(self, case: Path, *records: Mapping[str, object], thread: str | None = None) -> None:
        lines = read_file_lines(case, thread)
        first = sum(1 for line in lines if FINDING_HEADING.fullmatch(line)) + 1
        stamp = RoundStamp(number=1, day=DAY, head=self.git.head)
        rounds = (ROUND_HEADING.fullmatch(line) for line in lines)
        opened = any(found and int(found['round']) == stamp.number for found in rounds)
        text = write_findings(first, records) if opened else write_round(stamp, first, records)
        append_text(case, text, thread)

    def render(self, case: Path, *extra: str) -> CliRun:
        return self.run('render', '--case', str(case), *extra)

    def check(self, case: Path) -> CliRun:
        return self.run('check', '--case', str(case))

    def export(self, case: Path, lens: str, *extra: str, selection: str | None = None) -> CliRun:
        arguments = ('export', '--case', str(case), '--lens', lens, *extra)
        if selection is None:
            return self.run(*arguments, stdin='')

        self.selection_file.write_text(selection, encoding='utf-8')
        return self.run(*arguments, '--selection', str(self.selection_file))

    def export_from_stdin(self, case: Path, lens: str, selection: str) -> CliRun:
        return self.run('export', '--case', str(case), '--lens', lens, stdin=selection)
