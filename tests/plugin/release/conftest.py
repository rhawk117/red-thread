"""The release repository fixture."""

import os
import shutil
from typing import TYPE_CHECKING

import pytest

from tests.plugin.release.repository import (
    PYPROJECT,
    VERSION,
    ReleaseRepository,
    skip_without_tools,
)

if TYPE_CHECKING:
    from pathlib import Path


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
