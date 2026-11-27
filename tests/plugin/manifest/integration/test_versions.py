"""The plugin's version is the same in its manifest and in its project file."""

import tomllib
from typing import TYPE_CHECKING, Any

import pytest

from tests.codec import decode_json

if TYPE_CHECKING:
    from pathlib import Path


class TestPluginVersion:
    @pytest.fixture
    def manifest_version(self, repository_root: Path) -> str:
        manifest = repository_root.joinpath('.claude-plugin', 'plugin.json')
        return decode_json(manifest.read_text(encoding='utf-8'), dict[str, Any])['version']

    @pytest.fixture
    def project_version(self, repository_root: Path) -> str:
        project = repository_root.joinpath('pyproject.toml')
        return tomllib.loads(project.read_text(encoding='utf-8'))['project']['version']

    def test_manifest_and_project_file_name_the_same_version(
        self, manifest_version: str, project_version: str
    ) -> None:
        assert manifest_version == project_version
