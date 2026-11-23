"""A release repository: a working clone of main beside a bare origin, at version 0.1.0."""

import json
import shutil
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from tests.casefile.launcher.children import ChildRunner

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.launcher.children import Finished

REQUIRED_TOOLS = ('git', 'jq', 'uv')
VERSION = '0.1.0'
PYPROJECT = f'[project]\nname = "red-thread-plugin"\nversion = "{VERSION}"\n'
GIT_SETTINGS = ('-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null')


@dataclass(slots=True, kw_only=True, frozen=True)
class ReleaseRepository:
    root: Path
    origin: Path
    script: Path
    output: Path
    environment: dict[str, str]

    def git(self, *arguments: str, at: Path | None = None) -> str:
        runner = ChildRunner(cwd=at or self.root, env=self.environment)
        finished = runner.run('git', *GIT_SETTINGS, *arguments)
        assert finished.code == 0, finished.err
        return finished.out.strip()

    def write_manifest_version(self, version: str) -> None:
        self.root.joinpath('.claude-plugin', 'plugin.json').write_text(
            json.dumps({'name': 'red-thread', 'version': version}), encoding='utf-8'
        )

    def release(self, bump: str) -> Finished:
        runner = ChildRunner(cwd=self.root, env={**self.environment, 'VERSION_BUMP': bump})
        return runner.run('bash', str(self.script))


def skip_without_tools() -> None:
    missing = [tool for tool in REQUIRED_TOOLS if shutil.which(tool) is None]
    if missing:
        pytest.skip(f'the release script needs {", ".join(missing)}')
