"""The skills the plan skill loads declare their names, and the agent-only ones are not commands."""

from typing import TYPE_CHECKING

import pytest

from tests.plugin.frontmatter import read_frontmatter_lines, read_scalar

if TYPE_CHECKING:
    from pathlib import Path


def loaded_skill_cases() -> pytest.MarkDecorator:
    names = ('cross-examine', 'agents/risk-register', 'agents/break-it-down')
    return pytest.mark.parametrize('skill', [pytest.param(name, id=name) for name in names])


def agent_skill_cases() -> pytest.MarkDecorator:
    names = ('agents/risk-register', 'agents/break-it-down')
    return pytest.mark.parametrize('skill', [pytest.param(name, id=name) for name in names])


class TestLoadedSkills:
    @pytest.fixture
    def plan_text(self, repository_root: Path) -> str:
        return repository_root.joinpath('skills', 'plan', 'SKILL.md').read_text(encoding='utf-8')

    def read_skill_frontmatter(self, root: Path, skill: str) -> tuple[str, ...]:
        return read_frontmatter_lines(root.joinpath('skills', skill, 'SKILL.md'))

    @loaded_skill_cases()
    def test_skill_declares_its_directory_name(self, repository_root: Path, skill: str) -> None:
        lines = self.read_skill_frontmatter(repository_root, skill)

        assert read_scalar(lines, 'name') == skill.rpartition('/')[2]

    @loaded_skill_cases()
    def test_plan_names_the_skill_to_load(self, plan_text: str, skill: str) -> None:
        assert f'`red-thread:{skill.rpartition("/")[2]}`' in plan_text

    @agent_skill_cases()
    def test_agent_skill_is_not_a_command(self, repository_root: Path, skill: str) -> None:
        lines = self.read_skill_frontmatter(repository_root, skill)

        assert read_scalar(lines, 'user-invocable') == 'false'
