"""Every agent that navigates preloads the navigate skill, and the skill declares that name."""

from typing import TYPE_CHECKING, Any

import pytest

from tests.codec import decode_json
from tests.plugin.frontmatter import read_flow_list, read_frontmatter_lines, read_scalar

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def navigating_agent_cases() -> pytest.MarkDecorator:
    names = ('swarm/code-lens', 'swarm/code-sense', 'swarm/lab-rat', 'peer-review')
    return pytest.mark.parametrize('agent', [pytest.param(name, id=name) for name in names])


class TestNavigatePreload:
    @pytest.fixture
    def skill_frontmatter(self, repository_root: Path) -> tuple[str, ...]:
        return read_frontmatter_lines(
            repository_root.joinpath('skills', 'agents', 'navigate', 'SKILL.md')
        )

    def test_skill_declares_the_name_navigate(self, skill_frontmatter: Sequence[str]) -> None:
        assert read_scalar(skill_frontmatter, 'name') == 'navigate'

    def test_manifest_scans_the_directory_that_holds_the_skill(self, repository_root: Path) -> None:
        manifest = repository_root.joinpath('.claude-plugin', 'plugin.json')

        assert (
            './skills/agents/'
            in decode_json(manifest.read_text(encoding='utf-8'), dict[str, Any])['skills']
        )

    @navigating_agent_cases()
    def test_agent_preloads_navigate(self, repository_root: Path, agent: str) -> None:
        lines = read_frontmatter_lines(repository_root.joinpath('agents', f'{agent}.md'))

        assert 'navigate' in read_flow_list(lines, 'skills'), agent
