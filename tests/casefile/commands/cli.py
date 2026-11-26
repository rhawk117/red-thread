"""Drives red_thread_casefile.cli.main in-process and reports what a caller would see."""

import io
import json
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_casefile.cli import main

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from tests.casefile.ledger.git_repository import GitRepository


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
    def batch_file(self) -> Path:
        return self.git.root.parent.joinpath('batch.json')

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

    def add(
        self,
        case: Path,
        *records: dict[str, object],
        thread: str | None = None,
        round_number: int = 1,
    ) -> CliRun:
        self.batch_file.write_text(json.dumps(list(records)), encoding='utf-8')
        scope = ('--thread', thread) if thread is not None else ()
        return self.run(
            'add',
            '--case',
            str(case),
            '--round',
            str(round_number),
            '--file',
            str(self.batch_file),
            *scope,
        )

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

    def page(self, case: Path, url: str) -> CliRun:
        return self.run('page', '--case', str(case), '--url', url)
