"""GitSourceTree: line numbers count line feeds only, and exclude puts a pattern on its own line."""

import string
from typing import TYPE_CHECKING

import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from red_thread_casefile.store import GitSourceTree

from tests.casefile.ledger.git_repository import create_empty_repository

if TYPE_CHECKING:
    from pathlib import Path

LINE_SAFE = st.characters(blacklist_categories=('Cs',), blacklist_characters='\r\n')
SEPARATED = ['a\N{LINE SEPARATOR}b', 'c\x0cd', 'e\x85f\N{PARAGRAPH SEPARATOR}g', 'h']


def lacks_pattern(pair: tuple[str, str]) -> bool:
    initial, pattern = pair
    return pattern not in initial.split('\n')


class TestReadLinesProperties:
    lines = st.lists(st.text(alphabet=LINE_SAFE, max_size=20), max_size=6)
    last_lines = st.text(alphabet=LINE_SAFE, min_size=1, max_size=20)
    names = st.text(alphabet=string.ascii_letters, min_size=1, max_size=10)

    def create_tree(self, factory: pytest.TempPathFactory) -> GitSourceTree:
        return GitSourceTree(root=factory.mktemp('tree', numbered=True))

    @pytest.mark.regression
    @given(lines=lines)
    @example(lines=SEPARATED)
    def test_lines_are_numbered_by_line_feeds_only(
        self, tmp_path_factory: pytest.TempPathFactory, lines: list[str]
    ) -> None:
        tree = self.create_tree(tmp_path_factory)
        tree.root.joinpath('source.txt').write_text(''.join(f'{line}\n' for line in lines))

        assert tree.read_lines('source.txt') == tuple(lines)

    @pytest.mark.regression
    @given(lines=lines, last=last_lines)
    @example(lines=SEPARATED, last='i\N{LINE SEPARATOR}j')
    def test_a_last_line_without_a_line_feed_is_still_a_line(
        self, tmp_path_factory: pytest.TempPathFactory, lines: list[str], last: str
    ) -> None:
        tree = self.create_tree(tmp_path_factory)
        tree.root.joinpath('source.txt').write_text('\n'.join([*lines, last]))

        assert tree.read_lines('source.txt') == (*lines, last)

    @given(name=names)
    def test_a_path_that_is_not_a_file_has_no_lines(
        self, tmp_path_factory: pytest.TempPathFactory, name: str
    ) -> None:
        tree = self.create_tree(tmp_path_factory)
        tree.root.joinpath(f'dir-{name}').mkdir()

        assert tree.read_lines(name) is None
        assert tree.read_lines(f'dir-{name}') is None


class TestExcludeProperties:
    initial_texts = st.text(
        alphabet=st.characters(blacklist_categories=('Cs',), blacklist_characters='\r'), max_size=30
    )
    patterns = st.text(alphabet=LINE_SAFE, min_size=1, max_size=15)
    fresh = st.tuples(initial_texts, patterns).filter(lacks_pattern)
    text_lines = st.text(alphabet=LINE_SAFE, max_size=10)

    def create_excludes(
        self, factory: pytest.TempPathFactory, initial: str
    ) -> tuple[GitSourceTree, Path]:
        repository = create_empty_repository(factory.mktemp('repo', numbered=True))
        path = repository.root.joinpath('.git', 'info', 'exclude')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(initial, encoding='utf-8')
        return repository.tree, path

    @pytest.mark.regression
    @given(case=fresh)
    @example(case=('*.log', '.red-thread/'))
    @example(case=('*.log\n', '.red-thread/'))
    @example(case=('', '.red-thread/'))
    def test_a_new_pattern_lands_on_a_line_of_its_own_and_the_old_text_stays(
        self, tmp_path_factory: pytest.TempPathFactory, case: tuple[str, str]
    ) -> None:
        initial, pattern = case
        tree, path = self.create_excludes(tmp_path_factory, initial)

        tree.exclude(pattern)

        result = path.read_text(encoding='utf-8')
        assert pattern in result.split('\n')
        assert result.startswith(initial)
        assert result[len(initial) :] in {f'{pattern}\n', f'\n{pattern}\n'}

    @given(case=st.tuples(initial_texts, patterns))
    def test_excluding_the_same_pattern_twice_changes_nothing_the_second_time(
        self, tmp_path_factory: pytest.TempPathFactory, case: tuple[str, str]
    ) -> None:
        initial, pattern = case
        tree, path = self.create_excludes(tmp_path_factory, initial)
        tree.exclude(pattern)
        once = path.read_text(encoding='utf-8')

        tree.exclude(pattern)

        assert path.read_text(encoding='utf-8') == once
        assert pattern in once.split('\n')

    @given(before=text_lines, pattern=patterns, after=text_lines)
    def test_a_pattern_already_listed_is_left_alone(
        self, tmp_path_factory: pytest.TempPathFactory, before: str, pattern: str, after: str
    ) -> None:
        initial = f'{before}\n{pattern}\n{after}'
        tree, path = self.create_excludes(tmp_path_factory, initial)

        tree.exclude(pattern)

        assert path.read_text(encoding='utf-8') == initial
