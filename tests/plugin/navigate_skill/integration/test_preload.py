"""Every agent that navigates preloads the navigate skill, and the skill declares that name."""

import re
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


def navigating_agent_cases() -> pytest.MarkDecorator:
    names = ('code-lens', 'code-sense', 'research-cell', 'peer-review')
    return pytest.mark.parametrize('agent', [pytest.param(name, id=name) for name in names])


def read_frontmatter_lines(file: Path) -> tuple[str, ...]:
    lines = file.read_text(encoding='utf-8').splitlines()
    assert lines[0] == '---'
    closing = lines.index('---', 1)
    return tuple(lines[1:closing])


def read_scalar(lines: tuple[str, ...], key: str) -> str | None:
    values = [line.partition(':')[2].strip() for line in lines if line.startswith(f'{key}:')]
    return next(iter(values), None)


def read_flow_list(lines: tuple[str, ...], key: str) -> tuple[str, ...]:
    value = read_scalar(lines, key) or ''
    items = re.fullmatch(r'\[(.*)\]', value)
    if not items:
        return ()

    return tuple(item.strip() for item in items.group(1).split(',') if item.strip())


class TestNavigatePreload:
    @pytest.fixture
    def skill_frontmatter(self, repository_root: Path) -> tuple[str, ...]:
        return read_frontmatter_lines(repository_root.joinpath('skills', 'navigate', 'SKILL.md'))

    def test_skill_declares_the_name_navigate(self, skill_frontmatter: tuple[str, ...]) -> None:
        assert read_scalar(skill_frontmatter, 'name') == 'navigate'

    @navigating_agent_cases()
    def test_agent_preloads_navigate(self, repository_root: Path, agent: str) -> None:
        lines = read_frontmatter_lines(repository_root.joinpath('agents', f'{agent}.md'))

        assert 'navigate' in read_flow_list(lines, 'skills'), agent
