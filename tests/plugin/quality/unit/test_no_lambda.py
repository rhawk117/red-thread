"""No tracked Python file uses lambda: a callable handed to an API is a named function."""

import ast
from typing import TYPE_CHECKING

import pytest

from tests.casefile.launcher.children import ChildRunner

if TYPE_CHECKING:
    from pathlib import Path


def find_lambda_sites(path: Path, root: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    location = path.relative_to(root)
    return [f'{location}:{node.lineno}' for node in ast.walk(tree) if isinstance(node, ast.Lambda)]


@pytest.mark.agents
class TestNoLambda:
    @pytest.fixture
    def python_files(self, repository_root: Path) -> list[Path]:
        listed = ChildRunner(cwd=repository_root).run('git', 'ls-files', '-z', '--', '*.py')
        return [repository_root.joinpath(name) for name in listed.out.split('\0') if name]

    def test_git_lists_the_tracked_python_files(
        self, repository_root: Path, python_files: list[Path]
    ) -> None:
        assert repository_root.joinpath('conftest.py') in python_files

    def test_no_tracked_python_file_uses_lambda(
        self, repository_root: Path, python_files: list[Path]
    ) -> None:
        sites = [site for path in python_files for site in find_lambda_sites(path, repository_root)]
        assert sites == []
