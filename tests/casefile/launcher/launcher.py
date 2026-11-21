"""scripts/casefile.sh as a caller outside the plugin runs it: a child process in a repository."""

import os
import shutil
from dataclasses import dataclass
from typing import TYPE_CHECKING

from tests.casefile.launcher.children import ChildRunner

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from tests.casefile.launcher.children import Finished
    from tests.casefile.ledger.git_repository import GitRepository

PLUGIN_ROOT = 'CLAUDE_PLUGIN_ROOT'
OUTER_VARIABLES = frozenset({PLUGIN_ROOT, 'VIRTUAL_ENV'})
TARGET = 'why the retry queue stalls'


def list_tree(root: Path) -> list[str]:
    return sorted(str(path.relative_to(root)) for path in root.rglob('*'))


def read_outside_environment() -> dict[str, str]:
    return {name: value for name, value in os.environ.items() if name not in OUTER_VARIABLES}


@dataclass(slots=True, kw_only=True, frozen=True)
class PluginCopy:
    root: Path
    files: tuple[str, ...]

    @property
    def script(self) -> Path:
        return self.root.joinpath('scripts', 'casefile.sh')


def copy_plugin(source: Path, target: Path) -> PluginCopy:
    skipped = shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info', '.venv')
    package = target.joinpath('packages', 'casefile')
    shutil.copytree(source.joinpath('packages', 'casefile'), package, ignore=skipped)
    target.joinpath('scripts').mkdir()
    shutil.copy2(source.joinpath('scripts', 'casefile.sh'), target.joinpath('scripts'))
    return PluginCopy(root=target, files=tuple(list_tree(target)))


@dataclass(slots=True, kw_only=True, frozen=True)
class Launcher:
    plugin: PluginCopy
    git: GitRepository
    environment: Mapping[str, str]

    def run(self, *arguments: str, stdin: str = '') -> Finished:
        runner = ChildRunner(cwd=self.git.root, env=self.environment)
        return runner.run('sh', str(self.plugin.script), *arguments, stdin=stdin)

    def run_rooted_at(self, root: Path, *arguments: str) -> Finished:
        environment = {**self.environment, PLUGIN_ROOT: str(root)}
        runner = ChildRunner(cwd=self.git.root, env=environment)
        return runner.run('sh', str(self.plugin.script), *arguments)

    def init(self) -> Path:
        finished = self.run('init', '--target', TARGET, '--kind', 'root-cause', '--bar', 'a line')
        assert finished.code == 0, finished.err
        created = finished.out.splitlines()[0].removeprefix('created ')
        return self.git.root.joinpath(created).resolve()

    def add(self, case: Path, batch: str) -> Finished:
        return self.run('add', '--case', str(case), '--round', '1', stdin=batch)

    def on_case(self, command: str, case: Path, *extra: str) -> Finished:
        return self.run(command, '--case', str(case), *extra)
