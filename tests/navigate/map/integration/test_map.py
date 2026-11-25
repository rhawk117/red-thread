"""Mapping a real directory: ranking by references, budget rungs, notes and the empty case."""

from typing import TYPE_CHECKING

import pytest
from red_thread_navigate.budget import estimate_tokens

from tests.navigate.samples import BIG_BUDGET, CLIENT, NAVIGATOR
from tests.navigate.symbols.samples import SourceDir

if TYPE_CHECKING:
    from pathlib import Path

CORE = """\
def helper():
    return 1


def rarely():
    return 2


class Widget:
    def render(self):
        return helper()
"""
HOT = 'def hot():\n    pass\n\n\ndef use():\n    hot()\n    hot()\n'


@pytest.fixture
def source(tmp_path: Path) -> SourceDir:
    return SourceDir(root=tmp_path)


class TestRanking:
    @pytest.fixture
    def project(self, source: SourceDir) -> SourceDir:
        source.write('core.py', CORE)
        source.write('client.py', CLIENT)
        return source

    def test_directory_lists_symbols_with_addresses_most_referenced_first(
        self, project: SourceDir
    ) -> None:
        text = NAVIGATOR.map(project.root, budget=BIG_BUDGET)

        assert 'core.py#Widget.render' in text
        assert 'L1-L2' in text
        assert text.index('core.py#helper') < text.index('core.py#rarely')
        assert text.index('core.py  ') < text.index('client.py  ')

    def test_file_lists_its_full_outline(self, project: SourceDir) -> None:
        text = NAVIGATOR.map(project.root / 'core.py', budget=BIG_BUDGET)

        assert 'client.py' not in text
        assert all(
            address in text
            for address in (
                'core.py#helper',
                'core.py#rarely',
                'core.py#Widget',
                'core.py#Widget.render',
            )
        )

    def test_file_outline_is_in_source_order(self, project: SourceDir) -> None:
        text = NAVIGATOR.map(project.root / 'core.py', budget=BIG_BUDGET)

        assert (
            text.index('core.py#helper')
            < text.index('core.py#rarely')
            < text.index('core.py#Widget')
        )


class TestBudget:
    @pytest.fixture
    def crowded(self, source: SourceDir) -> SourceDir:
        for number in range(40):
            source.write(f'm{number:02}.py', f'def f{number}():\n    return 1\n')
        source.write('zz_hot.py', HOT)
        return source

    @pytest.fixture
    def crowded_with_notes(self, source: SourceDir) -> SourceDir:
        source.write('broken.py', 'def (:\n')
        for number in range(40):
            source.write(f'm{number:02}.py', f'def f{number}():\n    return 1\n')
        source.root.joinpath('blob.bin').write_bytes(b'\0\1\2')
        return source

    @pytest.fixture
    def unparsable(self, source: SourceDir) -> SourceDir:
        for number in range(30):
            source.write(f'bad{number:02}.py', 'def (:\n')
        return source

    def test_small_budget_steps_down_and_keeps_the_most_referenced_file(
        self, crowded: SourceDir
    ) -> None:
        full = NAVIGATOR.map(crowded.root, budget=BIG_BUDGET)
        small = NAVIGATOR.map(crowded.root, budget=150)

        assert 'zz_hot.py#hot' in full
        assert '#' not in small
        assert 'zz_hot.py' in small.splitlines()[1]
        assert 'raise --budget' in small

    def test_notes_come_first_and_survive_a_cut(self, crowded_with_notes: SourceDir) -> None:
        text = NAVIGATOR.map(crowded_with_notes.root, budget=64)

        lines = text.splitlines()
        assert lines[0].startswith('skipped 1 binary')
        assert 'broken.py: syntax error' in lines[1]
        assert 'raise --budget' in text

    def test_many_unparsable_files_stay_within_the_budget(self, unparsable: SourceDir) -> None:
        text = NAVIGATOR.map(unparsable.root, budget=64)

        assert estimate_tokens(text) <= 64
        assert 'more notes' in text


class TestEmptyDirectory:
    @pytest.fixture
    def notes_only(self, source: SourceDir) -> SourceDir:
        source.write('notes.txt', 'hello\n')
        return source

    def test_names_languages_suffixes_and_next_step(self, notes_only: SourceDir) -> None:
        text = NAVIGATOR.map(notes_only.root, budget=BIG_BUDGET)

        assert 'No file navigate can read' in text
        assert 'python (.py, .pyi)' in text
        assert 'javascript (.cjs, .js, .jsx, .mjs)' in text
        assert 'Next step' in text

    def test_message_is_fitted_to_the_budget(self, notes_only: SourceDir) -> None:
        text = NAVIGATOR.map(notes_only.root, budget=32)

        assert estimate_tokens(text) <= 32
