"""The artifact-authoring skill reaches its readers and leaves briefs to meet-the-team."""

from typing import TYPE_CHECKING

import pytest

from tests.plugin.frontmatter import read_flow_list, read_frontmatter_lines, read_scalar

if TYPE_CHECKING:
    from pathlib import Path


def primary_skill_cases() -> pytest.MarkDecorator:
    names = ('investigate', 'debug', 'distill', 'plan')
    return pytest.mark.parametrize('skill', [pytest.param(name, id=name) for name in names])


class TestArtifactAuthoring:
    listed_name = 'red-thread:artifact-authoring'

    @pytest.fixture
    def skill_file(self, repository_root: Path) -> Path:
        return repository_root.joinpath('skills', 'agents', 'artifact-authoring', 'SKILL.md')

    @pytest.fixture
    def skill_frontmatter(self, skill_file: Path) -> tuple[str, ...]:
        return read_frontmatter_lines(skill_file)

    @pytest.fixture
    def skill_text(self, skill_file: Path) -> str:
        return skill_file.read_text(encoding='utf-8')

    @pytest.fixture
    def lead_frontmatter(self, repository_root: Path) -> tuple[str, ...]:
        return read_frontmatter_lines(repository_root.joinpath('agents', 'research-lead.md'))

    def test_skill_declares_the_name_artifact_authoring(
        self, skill_frontmatter: tuple[str, ...]
    ) -> None:
        assert read_scalar(skill_frontmatter, 'name') == 'artifact-authoring'

    def test_skill_is_not_a_command(self, skill_frontmatter: tuple[str, ...]) -> None:
        assert read_scalar(skill_frontmatter, 'user-invocable') == 'false'

    def test_research_lead_preloads_the_skill(self, lead_frontmatter: tuple[str, ...]) -> None:
        assert 'artifact-authoring' in read_flow_list(lead_frontmatter, 'skills')

    @primary_skill_cases()
    def test_primary_skill_names_the_skill_to_load(self, repository_root: Path, skill: str) -> None:
        text = repository_root.joinpath('skills', skill, 'SKILL.md').read_text(encoding='utf-8')

        assert self.listed_name in text, skill

    def test_skill_sends_brief_writing_to_meet_the_team(self, skill_text: str) -> None:
        assert 'meet-the-team' in skill_text
