"""Framing a case in a real git repository: its head, its languages and its exclusion."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.packaged import load_wording
from red_thread_casefile.services import EXCLUDED, CaseFile, Framing
from red_thread_casefile.store import DirectoryCaseRepository
from red_thread_core.store import GitSourceTree

from tests.casefile.ledger.directory import create_directory_harness
from tests.casefile.ledger.memory import FixedClock

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.ledger.directory import DirectoryHarness
    from tests.casefile.ledger.git_repository import GitRepository

FRAMING = Framing(
    id='20261121-retry-queue-slowdown',
    target='why the retry queue stalls',
    kind='root-cause',
    bar='name the line that stalls it',
)


def read_exclusions(git: GitRepository) -> list[str]:
    path = git.root.joinpath('.git', 'info', 'exclude')
    return path.read_text(encoding='utf-8').splitlines() if path.is_file() else []


class TestFrameInGit:
    def test_case_is_recorded_with_the_real_head_and_the_languages_of_tracked_files(
        self, directory_harness: DirectoryHarness
    ) -> None:
        directory_harness.git.write('untracked.rs', 'fn main() {}\n')

        case = directory_harness.casefile.frame(FRAMING)

        assert case.head == directory_harness.git.head
        assert case.capabilities.languages == ('Python',)
        assert directory_harness.repository.read_case() == case

    def test_case_framed_before_the_first_commit_has_no_head(
        self, empty_repository: GitRepository
    ) -> None:
        harness = create_directory_harness(empty_repository)

        case = harness.casefile.frame(FRAMING)

        assert case.head is None
        assert case.capabilities.languages == ()

    def test_case_directory_is_untracked_and_hidden_from_git_status(
        self, directory_harness: DirectoryHarness
    ) -> None:
        directory_harness.casefile.frame(FRAMING)

        assert directory_harness.git.run('status', '--porcelain') == ''


class TestWithoutGit:
    @pytest.fixture
    def tree(self, git_repository: GitRepository, monkeypatch: pytest.MonkeyPatch) -> GitSourceTree:
        monkeypatch.setenv('PATH', str(git_repository.root.joinpath('no-tools')))
        return git_repository.tree

    def test_tree_has_no_head_and_no_files_when_git_is_not_installed(
        self, tree: GitSourceTree
    ) -> None:
        assert tree.get_head() is None
        assert tree.list_files() == ()


class TestExclusion:
    def test_excluded_once_however_often_it_is_asked(self, git_repository: GitRepository) -> None:
        tree = git_repository.tree

        tree.exclude(EXCLUDED)
        tree.exclude(EXCLUDED)
        tree.exclude(EXCLUDED)

        assert read_exclusions(git_repository).count(EXCLUDED) == 1

    def test_excluded_once_across_several_cases_in_one_repository(
        self, directory_harness: DirectoryHarness
    ) -> None:
        directory_harness.casefile.frame(FRAMING)
        second_directory = directory_harness.git.root.joinpath('.red-thread', 'second-case')
        second = CaseFile(
            repository=DirectoryCaseRepository(directory=second_directory),
            tree=GitSourceTree(root=directory_harness.git.root),
            clock=FixedClock(),
            wording=load_wording(),
        )

        second.frame(FRAMING)

        assert read_exclusions(directory_harness.git).count(EXCLUDED) == 1

    def test_existing_exclusions_are_kept(self, git_repository: GitRepository) -> None:
        exclude = git_repository.root.joinpath('.git', 'info', 'exclude')
        exclude.parent.mkdir(parents=True, exist_ok=True)
        exclude.write_text('# mine\nbuild/\n', encoding='utf-8')

        git_repository.tree.exclude(EXCLUDED)

        assert read_exclusions(git_repository)[-3:] == ['# mine', 'build/', EXCLUDED][-3:]
        assert 'build/' in read_exclusions(git_repository)

    def test_exclusion_is_its_own_line_when_the_file_has_no_final_newline(
        self, git_repository: GitRepository
    ) -> None:
        exclude = git_repository.root.joinpath('.git', 'info', 'exclude')
        exclude.parent.mkdir(parents=True, exist_ok=True)
        exclude.write_text('build/', encoding='utf-8')

        git_repository.tree.exclude(EXCLUDED)

        assert read_exclusions(git_repository) == ['build/', EXCLUDED]

    def test_directory_outside_any_repository_is_left_alone(self, tmp_path: Path) -> None:
        plain = tmp_path.joinpath('plain')
        plain.mkdir()
        tree = GitSourceTree(root=plain)

        tree.exclude(EXCLUDED)

        assert list(plain.iterdir()) == []
        assert tree.get_head() is None
        assert tree.list_files() == ()
