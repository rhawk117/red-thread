"""Walking a real directory and a real git repository for the source files under a path."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from red_thread_navigate.walk import SkipTally, walk

from tests.casefile.launcher.children import ChildRunner

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_navigate.walk import Walk

GIT_SETTINGS = (
    '-c',
    'user.name=test',
    '-c',
    'user.email=test@example.invalid',
    '-c',
    'commit.gpgsign=false',
    '-c',
    'core.hooksPath=/dev/null',
)
OVER_LIMIT = 1024 * 1024 + 1


@dataclass(slots=True, kw_only=True, frozen=True)
class Tree:
    root: Path
    outside: Path

    def write(self, path: str, text: str = 'x = 1\n') -> None:
        target = self.root.joinpath(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8')

    def write_bytes(self, path: str, data: bytes) -> None:
        target = self.root.joinpath(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def git(self, *arguments: str) -> None:
        finished = ChildRunner(cwd=self.root).run('git', *GIT_SETTINGS, *arguments)
        assert finished.code == 0, finished.err

    def init_git(self) -> None:
        self.git('init', '--quiet')

    def commit_all(self) -> None:
        self.git('add', '--all')
        self.git('commit', '--quiet', '--message', 'files')


def paths_of(result: Walk) -> list[str]:
    return [file.path.as_posix() for file in result.files]


@pytest.fixture
def tree(tmp_path: Path) -> Tree:
    root = tmp_path.joinpath('root')
    outside = tmp_path.joinpath('outside')
    root.mkdir()
    outside.mkdir()
    outside.joinpath('secret.py').write_text('secret = 1\n', encoding='utf-8')
    return Tree(root=root, outside=outside)


class TestInGitWorkTree:
    @pytest.fixture
    def repository(self, tree: Tree) -> Tree:
        tree.init_git()
        tree.write('b.py')
        tree.write('pkg/a.py', 'a = 1\n')
        tree.write('build/kept.py')
        tree.write('.hidden/kept.py')
        tree.write('.gitignore', 'ignored.py\n')
        tree.commit_all()
        tree.write('untracked.py')
        tree.write('ignored.py')
        return tree

    def test_only_tracked_files_are_listed_sorted_by_path(self, repository: Tree) -> None:
        result = walk(repository.root)

        assert paths_of(result) == [
            '.gitignore',
            '.hidden/kept.py',
            'b.py',
            'build/kept.py',
            'pkg/a.py',
        ]
        assert result.files[4].text == 'a = 1\n'

    def test_a_subdirectory_lists_paths_relative_to_it(self, repository: Tree) -> None:
        assert paths_of(walk(repository.root.joinpath('pkg'))) == ['a.py']

    def test_a_repository_cannot_run_a_program_through_its_own_config(
        self, repository: Tree
    ) -> None:
        marker = repository.outside.joinpath('ran')
        monitor = repository.outside.joinpath('monitor.sh')
        monitor.write_text(f'#!/bin/sh\ntouch {marker}\n', encoding='utf-8')
        monitor.chmod(0o755)
        repository.git('config', 'core.fsmonitor', str(monitor))

        walk(repository.root)

        assert not marker.exists()


class TestWithoutGit:
    def test_dot_directories_and_the_skip_list_are_left_out(self, tree: Tree) -> None:
        tree.write('src/main.py')
        tree.write('.git/config')
        tree.write('.cache/x.py')
        tree.write('node_modules/pkg/index.js')
        tree.write('src/__pycache__/main.pyc')
        tree.write('build/out.py')
        tree.write('venv/lib/site-packages/x.py')

        assert paths_of(walk(tree.root)) == ['src/main.py']

    def test_a_root_that_is_a_single_file_walks_to_that_file(self, tree: Tree) -> None:
        tree.write('one.py', 'one = 1\n')
        tree.write('two.py')

        result = walk(tree.root.joinpath('one.py'))

        assert paths_of(result) == ['one.py']
        assert result.files[0].text == 'one = 1\n'


class TestSkippedFiles:
    @pytest.fixture
    def skipped(self, tree: Tree) -> Tree:
        tree.write('ok.py')
        tree.write('big.py', 'a' * OVER_LIMIT)
        tree.write_bytes('image.bin', b'PNG\0\0data')
        tree.write_bytes('latin.py', b'caf\xe9\n')
        return tree

    def test_each_kind_is_skipped_and_counted_in_a_one_line_note(self, skipped: Tree) -> None:
        result = walk(skipped.root)

        assert paths_of(result) == ['ok.py']
        assert result.skipped == SkipTally(too_large=1, binary=1, not_utf8=1)
        assert result.note == 'skipped 1 over 1 MiB, 1 binary, 1 not UTF-8'

    def test_a_file_of_exactly_one_mebibyte_is_kept(self, tree: Tree) -> None:
        tree.write('edge.py', 'a' * (OVER_LIMIT - 1))

        assert paths_of(walk(tree.root)) == ['edge.py']

    def test_a_nul_byte_past_the_first_eight_kibibytes_is_not_binary(self, tree: Tree) -> None:
        tree.write_bytes('late.py', b'a' * 8192 + b'\0')

        assert paths_of(walk(tree.root)) == ['late.py']

    def test_there_is_no_note_when_nothing_was_skipped(self, tree: Tree) -> None:
        tree.write('ok.py')

        assert walk(tree.root).note is None


class TestSymlinksOutsideTheRoot:
    @pytest.fixture
    def linked(self, tree: Tree) -> Tree:
        tree.write('real.py')
        tree.root.joinpath('file_link.py').symlink_to(tree.outside.joinpath('secret.py'))
        tree.root.joinpath('dir_link').symlink_to(tree.outside, target_is_directory=True)
        tree.root.joinpath('inner_link.py').symlink_to(tree.root.joinpath('real.py'))
        return tree

    def test_a_directory_walk_neither_follows_nor_lists_them(self, linked: Tree) -> None:
        result = walk(linked.root)

        assert paths_of(result) == ['inner_link.py', 'real.py']
        assert result.skipped == SkipTally(outside_root=2)
        assert result.note == 'skipped 2 outside the root'

    def test_a_git_walk_neither_follows_nor_lists_them(self, linked: Tree) -> None:
        linked.init_git()
        linked.commit_all()

        result = walk(linked.root)

        assert paths_of(result) == ['inner_link.py', 'real.py']
        assert result.skipped == SkipTally(outside_root=2)
