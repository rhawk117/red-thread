"""The plan skill links every reference it ships, and its example draft is a plan revise reads."""

import re
from typing import TYPE_CHECKING

import pytest
from red_thread_plans.domain import PlanDraft
from red_thread_plans.schemas import decode_draft

from tests.plugin.frontmatter import read_frontmatter_lines, read_scalar

if TYPE_CHECKING:
    from pathlib import Path


class TestPlanSkill:
    json_block = re.compile(r'```json\n(.*?)```', re.DOTALL)

    @pytest.fixture
    def skill_directory(self, repository_root: Path) -> Path:
        return repository_root.joinpath('skills', 'plan')

    @pytest.fixture
    def skill_file(self, skill_directory: Path) -> Path:
        return skill_directory.joinpath('SKILL.md')

    @pytest.fixture
    def reference_names(self, skill_directory: Path) -> tuple[str, ...]:
        return tuple(sorted(path.name for path in skill_directory.glob('references/*.md')))

    @pytest.fixture
    def draft_examples(self, skill_directory: Path) -> tuple[str, ...]:
        text = skill_directory.joinpath('references', 'draft.md').read_text(encoding='utf-8')
        return tuple(self.json_block.findall(text))

    def test_skill_declares_the_name_plan(self, skill_file: Path) -> None:
        assert read_scalar(read_frontmatter_lines(skill_file), 'name') == 'plan'

    def test_skill_links_every_reference(
        self, skill_file: Path, reference_names: tuple[str, ...]
    ) -> None:
        text = skill_file.read_text(encoding='utf-8')

        assert [name for name in reference_names if f'(references/{name})' not in text] == []

    def test_draft_reference_holds_an_example(self, draft_examples: tuple[str, ...]) -> None:
        assert draft_examples

    def test_example_draft_decodes_as_a_plan(self, draft_examples: tuple[str, ...]) -> None:
        decoded = [decode_draft(example) for example in draft_examples]

        assert all(isinstance(draft, PlanDraft) for draft in decoded), decoded
