"""bin/redthread-plan from outside the plugin: a child process beside a case the case file made."""

import json
from typing import TYPE_CHECKING

import pytest

from tests.casefile.launcher.launcher import list_tree
from tests.casefile.ledger.builders import KNOWN
from tests.plans.document.builders import SOUND_SECTIONS, edit_plan, fill_plan

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.launcher.launcher import Launcher

DECISION = {'kind': 'decision', 'text': 'cap each job at five attempts', 'source': 'user'}
GROUNDS = json.dumps([KNOWN, DECISION])


class TestPlanScript:
    @pytest.fixture
    def plan(self, launcher: Launcher) -> Path:
        case = launcher.init()
        added = launcher.add(case, GROUNDS)
        assert added.code == 0, added.err
        return launcher.init_plan(case)

    @pytest.fixture
    def written(self, plan: Path) -> Path:
        plan.write_text(fill_plan(plan.read_text(encoding='utf-8'), SOUND_SECTIONS), 'utf-8')
        return plan

    def test_a_written_plan_passes_its_check(self, launcher: Launcher, written: Path) -> None:
        finished = launcher.run_plan('check', '--plan', str(written))

        assert finished.code == 0, finished.err
        assert finished.out.startswith(f'checked {written}: ')

    def test_a_plan_without_its_closing_fence_keeps_its_exit_code_and_its_reason(
        self, launcher: Launcher, written: Path
    ) -> None:
        text = edit_plan(written.read_text(encoding='utf-8'), (('---\n\n#', '\n#'),))
        written.write_text(text, encoding='utf-8')

        finished = launcher.run_plan('check', '--plan', str(written))

        assert finished.code == 1
        assert 'its frontmatter has no closing --- line' in finished.err

    def test_the_plugin_is_left_as_it_was(self, launcher: Launcher, written: Path) -> None:
        launcher.run_plan('check', '--plan', str(written))

        assert list_tree(launcher.plugin.root) == list(launcher.plugin.files)
