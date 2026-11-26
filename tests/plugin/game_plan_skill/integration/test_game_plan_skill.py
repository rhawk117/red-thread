"""game-plan links every reference it ships, and its example plan is one check can read."""

import re
from typing import TYPE_CHECKING

import pytest
from red_thread_plans.domain import PlanDocument
from red_thread_plans.policy import Grounds, PlanPolicy
from red_thread_plans.schemas import read_plan

from tests.plugin.frontmatter import read_frontmatter_lines, read_scalar

if TYPE_CHECKING:
    from pathlib import Path


class TestGamePlanSkill:
    markdown_block = re.compile(r'```markdown\n(.*?)```', re.DOTALL)

    @pytest.fixture
    def skill_directory(self, repository_root: Path) -> Path:
        return repository_root.joinpath('skills', 'game-plan')

    @pytest.fixture
    def skill_file(self, skill_directory: Path) -> Path:
        return skill_directory.joinpath('SKILL.md')

    @pytest.fixture
    def reference_names(self, skill_directory: Path) -> tuple[str, ...]:
        return tuple(sorted(path.name for path in skill_directory.glob('references/*.md')))

    @pytest.fixture
    def plan_examples(self, skill_directory: Path) -> tuple[str, ...]:
        text = skill_directory.joinpath('references', 'plan.md').read_text(encoding='utf-8')
        return tuple(self.markdown_block.findall(text))

    def read_example(self, example: str) -> PlanDocument:
        document = read_plan(example)
        assert isinstance(document, PlanDocument), document
        return document

    def test_skill_declares_the_name_game_plan(self, skill_file: Path) -> None:
        assert read_scalar(read_frontmatter_lines(skill_file), 'name') == 'game-plan'

    def test_skill_links_every_reference(
        self, skill_file: Path, reference_names: tuple[str, ...]
    ) -> None:
        text = skill_file.read_text(encoding='utf-8')

        assert [name for name in reference_names if f'(references/{name})' not in text] == []

    def test_plan_reference_holds_an_example(self, plan_examples: tuple[str, ...]) -> None:
        assert plan_examples

    def test_example_plan_has_every_section_check_asks_for(
        self, plan_examples: tuple[str, ...]
    ) -> None:
        documents = tuple(map(self.read_example, plan_examples))
        policies = (
            PlanPolicy(document=document, grounds=Grounds(), missing=document.frontmatter.cases)
            for document in documents
        )

        assert [policy.get_section_issues() for policy in policies] == [()] * len(documents)
