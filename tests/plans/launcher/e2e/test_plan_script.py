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

    from tests.casefile.launcher.launcher import Launcher

DECISION = {'kind': 'decision', 'text': 'keep one writer', 'source': 'user'}
GROUNDS = json.dumps([KNOWN, DECISION])
PLAN = msgspec.json.encode(create_valid_draft()).decode()


class TestPlanScript:
    @pytest.fixture
    def grounded(self, launcher: Launcher) -> Path:
        case = launcher.init()
        added = launcher.add(case, GROUNDS)
        assert added.code == 0, added.err
        return case

    def test_a_sound_plan_is_stored_and_its_page_written(
        self, launcher: Launcher, grounded: Path
    ) -> None:
        finished = launcher.revise(grounded, PLAN)

        assert finished.code == 0, finished.err
        assert finished.out.startswith('stored revision 1 at ')
        assert grounded.joinpath('plan.html').is_file()

    def test_a_plan_that_is_not_json_keeps_its_exit_code_and_its_reason(
        self, launcher: Launcher, grounded: Path
    ) -> None:
        finished = launcher.revise(grounded, '{"intent": ')

        assert finished.code == 1
        assert 'the plan cannot be read: it is not JSON' in finished.err

    def test_the_plugin_is_left_as_it_was(self, launcher: Launcher, grounded: Path) -> None:
        launcher.revise(grounded, PLAN)

        assert list_tree(launcher.plugin.root) == list(launcher.plugin.files)
