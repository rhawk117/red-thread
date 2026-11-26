"""A real git repository in a temporary directory, for the tiers that touch git."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_core.store import GitSourceTree

from tests.git import GIT_SETTINGS

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(slots=True, kw_only=True, frozen=True)
class GitRepository:
    root: Path

    @property
    def tree(self) -> GitSourceTree:
        return GitSourceTree(root=self.root)

    def run(self, *arguments: str) -> str:
        finished = self.tree.run_git(*GIT_SETTINGS, *arguments)
        assert finished is not None, f'git {" ".join(arguments)} failed in {self.root}'
        return finished

    def write(self, path: str, text: str) -> None:
        target = self.root.joinpath(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')

    def commit(self, message: str) -> str:
        self.run('add', '--all')
        self.run('commit', '--quiet', '--message', message)
        return self.head

    @property
    def head(self) -> str:
        return self.run('rev-parse', 'HEAD')


def create_empty_repository(root: Path) -> GitRepository:
    root.mkdir(parents=True, exist_ok=True)
    repository = GitRepository(root=root)
    repository.run('init', '--quiet')
    return repository
