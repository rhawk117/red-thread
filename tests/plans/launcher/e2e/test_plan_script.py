"""bin/redthread-plan from outside the plugin: a child process beside a case the case file made."""

import json
from typing import TYPE_CHECKING

import msgspec
import pytest

from tests.casefile.launcher.launcher import list_tree
from tests.casefile.ledger.builders import KNOWN
from tests.plans.revisions.builders import create_valid_draft

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.launcher.children import Finished
    from tests.casefile.launcher.launcher import Launcher

DECISION = {'kind': 'decision', 'text': 'keep one writer', 'source': 'user'}
GROUNDS = json.dumps([KNOWN, DECISION])


class TestPlanScript:
    @pytest.fixture
    def grounded(self, launcher: Launcher) -> Path:
        case = launcher.init()
        added = launcher.add(case, GROUNDS)
        assert added.code == 0, added.err
        return case

    @pytest.fixture
    def plan(self, launcher: Launcher) -> Path:
        return launcher.init_plan()

    def revise(self, launcher: Launcher, plan: Path, text: str) -> Finished:
        return launcher.run_plan('revise', '--plan', str(plan), stdin=text)

    def encode_plan(self, case: Path) -> str:
        return msgspec.json.encode(create_valid_draft(case.name)).decode()

    def test_a_sound_plan_is_stored_and_its_page_written(
        self, launcher: Launcher, grounded: Path, plan: Path
    ) -> None:
        finished = self.revise(launcher, plan, self.encode_plan(grounded))
        rendered = launcher.run_plan('render', '--plan', str(plan))

        assert finished.code == 0, finished.err
        assert finished.out.startswith('stored revision 1 at ')
        assert rendered.code == 0, rendered.err
        assert plan.joinpath('plan.html').is_file()

    def test_a_plan_that_is_not_json_keeps_its_exit_code_and_its_reason(
        self, launcher: Launcher, plan: Path
    ) -> None:
        finished = self.revise(launcher, plan, '{"intent": ')

        assert finished.code == 1
        assert 'the plan cannot be read: it is not JSON' in finished.err

    def test_the_plugin_is_left_as_it_was(
        self, launcher: Launcher, grounded: Path, plan: Path
    ) -> None:
        self.revise(launcher, plan, self.encode_plan(grounded))

        assert list_tree(launcher.plugin.root) == list(launcher.plugin.files)
