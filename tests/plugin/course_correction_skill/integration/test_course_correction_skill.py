"""course-correction declares its name and names what it loads, and game-plan points at it."""

from typing import TYPE_CHECKING

import pytest

from tests.plugin.frontmatter import read_frontmatter_lines, read_scalar

if TYPE_CHECKING:
    from pathlib import Path


def loaded_skill_cases() -> pytest.MarkDecorator:
    names = ('meet-the-team', 'artifact-authoring', 'cross-examine', 'break-it-down')
    return pytest.mark.parametrize('skill', [pytest.param(name, id=name) for name in names])


class TestCourseCorrectionSkill:
    @pytest.fixture
    def skill_file(self, repository_root: Path) -> Path:
        return repository_root.joinpath('skills', 'course-correction', 'SKILL.md')

    @pytest.fixture
    def skill_text(self, skill_file: Path) -> str:
        return skill_file.read_text(encoding='utf-8')

    def test_skill_declares_the_name_course_correction(self, skill_file: Path) -> None:
        assert read_scalar(read_frontmatter_lines(skill_file), 'name') == 'course-correction'

    @loaded_skill_cases()
    def test_skill_names_the_skill_to_load(self, skill_text: str, skill: str) -> None:
        assert f'`red-thread:{skill}`' in skill_text

    def test_game_plan_points_at_it_for_a_fork_in_the_road(self, repository_root: Path) -> None:
        text = repository_root.joinpath('skills', 'game-plan', 'SKILL.md').read_text(
            encoding='utf-8'
        )

        assert '`/red-thread:course-correction`' in text
