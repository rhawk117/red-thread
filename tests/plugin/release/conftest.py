"""A release repository: a working clone of main beside a bare origin, at version 0.1.0."""

import json
import os
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


@pytest.fixture
def release_repository(pytestconfig: pytest.Config, tmp_path: Path) -> ReleaseRepository:
    skip_without_tools()
    source = pytestconfig.rootpath
    root = tmp_path.joinpath('work')
    origin = tmp_path.joinpath('origin.git')
    output = tmp_path.joinpath('github-output')
    output.touch()
    environment = {
        **os.environ,
        'GITHUB_EVENT_NAME': 'workflow_dispatch',
        'GITHUB_REF': 'refs/heads/main',
        'REPOSITORY_IS_FORK': 'false',
        'GITHUB_OUTPUT': str(output),
    }
    environment.pop('CI', None)
    environment['NO_COLOR'] = '1'
    repository = ReleaseRepository(
        root=root,
        origin=origin,
        script=source.joinpath('.github', 'scripts', 'release.sh'),
        output=output,
        environment=environment,
    )
    origin.mkdir()
    root.joinpath('scripts').mkdir(parents=True)
    root.joinpath('.claude-plugin').mkdir()
    repository.git('init', '--quiet', '--bare', '--initial-branch=main', at=origin)
    repository.git('init', '--quiet', '--initial-branch=main')
    repository.git('config', 'user.name', 'test')
    repository.git('config', 'user.email', 'test@example.invalid')
    repository.git('remote', 'add', 'origin', str(origin))
    shutil.copy2(source.joinpath('scripts', 'log.sh'), root.joinpath('scripts'))
    root.joinpath('pyproject.toml').write_text(PYPROJECT, encoding='utf-8')
    repository.write_manifest_version(VERSION)
    repository.git('add', '--all')
    repository.git('commit', '--quiet', '--message', 'initial')
    repository.git('push', '--quiet', 'origin', 'main')
    return repository
