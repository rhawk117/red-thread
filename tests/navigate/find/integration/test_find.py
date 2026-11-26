"""Finding a name in a real directory: definitions first, references, no match and the budget."""

from typing import TYPE_CHECKING

import pytest
from red_thread_navigate.budget import estimate_tokens, fit_notes

from tests.navigate.samples import BIG_BUDGET, CLIENT, CORE, NAVIGATOR
from tests.navigate.symbols.samples import SourceDir

if TYPE_CHECKING:
    from pathlib import Path

SMALL_BUDGET = 40


def cut_budget_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('budget', [SMALL_BUDGET, 60, 120])


def noted_name_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('name', ['helper', 'missing'])


def noted_budget_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('budget', [SMALL_BUDGET, 64, 200])


@pytest.fixture
def source(tmp_path: Path) -> SourceDir:
    return SourceDir(root=tmp_path)


class TestFindInDirectory:
    @pytest.fixture
    def project(self, source: SourceDir) -> SourceDir:
        source.write('core.py', CORE)
        source.write('client.py', CLIENT)
        return source

    def test_definitions_come_before_references(self, project: SourceDir) -> None:
        text = NAVIGATOR.find('helper', project.root, budget=BIG_BUDGET)

        assert 'core.py#helper  function  L1-L2' in text
        assert 'client.py:5' in text
        assert 'client.py:6' in text
        assert 'core.py:7' in text
        assert text.index('core.py#helper') < text.index('client.py:5')

    def test_dotted_name_matches_the_qualified_ending(self, project: SourceDir) -> None:
        text = NAVIGATOR.find('Widget.render', project.root, budget=BIG_BUDGET)

        assert 'core.py#Widget.render  method' in text

    def test_unknown_name_suggests_a_next_step(self, project: SourceDir) -> None:
        text = NAVIGATOR.find('missing', project.root, budget=BIG_BUDGET)

        assert f'no matches for missing in {project.root}' in text
        assert f'map {project.root}' in text
        assert f'rg missing {project.root}' in text


class TestFindBudget:
    @pytest.fixture
    def crowded(self, source: SourceDir) -> SourceDir:
        source.write('core.py', CORE)
        for index in range(60):
            source.write(f'client{index}.py', CLIENT)
        return source

    @pytest.fixture
    def broken(self, source: SourceDir) -> SourceDir:
        source.write('broken.py', 'def (:\n')
        return source

    @pytest.fixture
    def noted(self, source: SourceDir) -> SourceDir:
        source.write('core.py', CORE)
        for index in range(30):
            source.write(f'broken{index}.py', 'def (:\n')
        return source

    @cut_budget_cases()
    def test_output_stays_within_budget_and_says_it_was_cut(
        self, crowded: SourceDir, budget: int
    ) -> None:
        text = NAVIGATOR.find('helper', crowded.root, budget=budget)

        assert estimate_tokens(text) <= budget
        assert 'raise --budget' in text

    def test_crowding_notes_are_cut_and_counted(self) -> None:
        notes = tuple(f'note number {index} about a file' for index in range(20))

        kept = fit_notes(notes, budget=100)

        assert kept[-1].endswith('more notes')
        assert kept[0] == 'note number 0 about a file'
        assert estimate_tokens('\n'.join(kept)) <= 100 // 4 + estimate_tokens(kept[-1])

    def test_a_syntax_error_note_too_long_for_its_share_is_still_counted(
        self, broken: SourceDir
    ) -> None:
        text = NAVIGATOR.find('helper', broken.root, budget=40)

        assert 'and 1 more notes' in text

    @noted_name_cases()
    @noted_budget_cases()
    def test_many_notes_keep_the_whole_output_within_budget(
        self, noted: SourceDir, name: str, budget: int
    ) -> None:
        text = NAVIGATOR.find(name, noted.root, budget=budget)

        assert estimate_tokens(text) <= budget
