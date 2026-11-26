"""The meet-the-team skill reaches its readers and introduces every agent on the roster."""

from typing import TYPE_CHECKING

import pytest

from tests.plugin.frontmatter import read_flow_list, read_frontmatter_lines, read_scalar
from tests.plugin.roster.cases import LEAD, SCOUTS, SKEPTIC

if TYPE_CHECKING:
    from pathlib import Path


def roster_agent_cases() -> pytest.MarkDecorator:
    names = (LEAD, SKEPTIC, *SCOUTS)
    return pytest.mark.parametrize('agent', [pytest.param(name, id=name) for name in names])


def primary_skill_cases() -> pytest.MarkDecorator:
    names = ('investigate', 'debug', 'plan')
    return pytest.mark.parametrize('skill', [pytest.param(name, id=name) for name in names])


class TestMeetTheTeam:
    listed_name = 'red-thread:meet-the-team'

    @pytest.fixture
    def skill_file(self, repository_root: Path) -> Path:
        return repository_root.joinpath('skills', 'agents', 'meet-the-team', 'SKILL.md')

    @pytest.fixture
    def skill_text(self, skill_file: Path) -> str:
        return skill_file.read_text(encoding='utf-8')

    @pytest.fixture
    def lead_frontmatter(self, repository_root: Path) -> tuple[str, ...]:
        return read_frontmatter_lines(repository_root.joinpath('agents', 'research-lead.md'))

    def test_skill_declares_the_name_meet_the_team(self, skill_file: Path) -> None:
        assert read_scalar(read_frontmatter_lines(skill_file), 'name') == 'meet-the-team'

    def test_research_lead_preloads_the_skill(self, lead_frontmatter: tuple[str, ...]) -> None:
        assert 'meet-the-team' in read_flow_list(lead_frontmatter, 'skills')

    @primary_skill_cases()
    def test_primary_skill_names_the_skill_to_load(self, repository_root: Path, skill: str) -> None:
        text = repository_root.joinpath('skills', skill, 'SKILL.md').read_text(encoding='utf-8')

        assert self.listed_name in text, skill

    @roster_agent_cases()
    def test_skill_names_every_agent_on_the_roster(self, skill_text: str, agent: str) -> None:
        assert f'`{agent}`' in skill_text, agent
