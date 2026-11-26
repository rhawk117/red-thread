"""Walking a real directory and a real git repository for the source files under a path."""

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from red_thread_navigate.walk import walk
from red_thread_navigate.walk.domain import tally_skips

from tests.casefile.launcher.children import ChildRunner
from tests.git import GIT_SETTINGS

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from red_thread_navigate.walk import Walk

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
        assert result.skipped == tally_skips(('too_large', 'binary', 'not_utf8'))
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
        assert result.skipped == tally_skips(('outside_root', 'outside_root'))
        assert result.note == 'skipped 2 outside the root'

    def test_a_git_walk_neither_follows_nor_lists_them(self, linked: Tree) -> None:
        linked.init_git()
        linked.commit_all()

        result = walk(linked.root)

        assert paths_of(result) == ['inner_link.py', 'real.py']
        assert result.skipped == tally_skips(('outside_root', 'outside_root'))


class TestSymlinksInsideTheRoot:
    @pytest.fixture
    def looped(self, tree: Tree) -> Tree:
        tree.write('pkg/a.py')
        tree.root.joinpath('pkg_link').symlink_to(
            tree.root.joinpath('pkg'), target_is_directory=True
        )
        return tree

    def test_a_directory_walk_does_not_follow_a_linked_directory(self, looped: Tree) -> None:
        result = walk(looped.root)

        assert paths_of(result) == ['pkg/a.py']
        assert result.note is None


class TestUnreadableEntries:
    @pytest.fixture
    def locked(self, tree: Tree) -> Iterator[Tree]:
        tree.write('ok.py')
        tree.write('locked.py')
        tree.write('closed/inner.py')
        tree.root.joinpath('locked.py').chmod(0o000)
        tree.root.joinpath('closed').chmod(0o000)
        if os.access(tree.root.joinpath('locked.py'), os.R_OK):
            tree.root.joinpath('closed').chmod(0o755)
            pytest.skip('the user reads files whatever their mode')
        yield tree
        tree.root.joinpath('closed').chmod(0o755)

    def test_a_directory_walk_skips_and_counts_what_it_cannot_read(self, locked: Tree) -> None:
        result = walk(locked.root)

        assert paths_of(result) == ['ok.py']
        assert result.skipped == tally_skips(('unreadable', 'unreadable'))
        assert result.note == 'skipped 2 unreadable'

    def test_a_git_walk_skips_and_counts_an_unreadable_file(self, tree: Tree) -> None:
        tree.write('ok.py')
        tree.write('locked.py')
        tree.init_git()
        tree.commit_all()
        tree.root.joinpath('locked.py').chmod(0o000)
        if os.access(tree.root.joinpath('locked.py'), os.R_OK):
            pytest.skip('the user reads files whatever their mode')

        result = walk(tree.root)

        assert paths_of(result) == ['ok.py']
        assert result.skipped == tally_skips(('unreadable',))


class TestGitListingFailure:
    def test_a_failed_listing_inside_a_work_tree_is_noted(self, tree: Tree) -> None:
        tree.write('a.py')
        tree.init_git()
        tree.commit_all()
        tree.root.joinpath('.git', 'index').write_bytes(b'garbage')

        result = walk(tree.root)

        assert paths_of(result) == ['a.py']
        assert result.note == 'git listing failed, walked the directory instead'

    def test_a_path_outside_any_work_tree_falls_back_without_a_note(self, tree: Tree) -> None:
        tree.write('a.py')

        assert walk(tree.root).note is None


class TestGitRefusesTheRepository:
    @pytest.fixture
    def refusing_git(self, tree: Tree, monkeypatch: pytest.MonkeyPatch) -> Tree:
        tree.write('a.py')
        tree.init_git()
        tree.commit_all()
        script = tree.outside.joinpath('bin', 'git')
        script.parent.mkdir()
        refusal = 'fatal: detected dubious ownership in repository at $2'
        script.write_text(f'#!/bin/sh\necho "{refusal}" >&2\nexit 128\n', encoding='utf-8')
        script.chmod(0o755)
        monkeypatch.setenv('PATH', str(script.parent))
        return tree

    def test_a_refusal_other_than_not_a_repository_is_noted_and_walks_the_directory(
        self, refusing_git: Tree
    ) -> None:
        result = walk(refusing_git.root)

        assert paths_of(result) == ['a.py']
        assert result.note == 'git listing failed, walked the directory instead'
