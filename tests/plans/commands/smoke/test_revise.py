"""redthread-plan revise, driven through main(argv) against a temporary git repository."""

from typing import TYPE_CHECKING

import msgspec
import pytest
from msgspec.structs import replace

from tests.casefile.ledger.builders import KNOWN
from tests.plans.revisions.builders import (
    create_valid_draft,
    plant_collision,
    plant_cycle,
    plant_groundless,
)

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_plans.domain import PlanDraft

    from tests.casefile.commands.cli import CliHarness
    from tests.plans.commands.cli import PlanHarness

DECISION = {'kind': 'decision', 'text': 'keep one writer', 'source': 'user'}


def encode(draft: PlanDraft) -> str:
    return msgspec.json.encode(draft).decode()


def list_revision_files(case: Path) -> list[str]:
    return sorted(path.name for path in case.joinpath('plans').glob('*'))


class TestRevise:
    @pytest.fixture
    def grounded(self, cli: CliHarness, case: Path) -> Path:
        added = cli.add(case, KNOWN, DECISION)
        assert added.code == 0, added.err
        return case

    def test_a_sound_plan_is_stored_as_revision_one_and_reported(
        self, planner: PlanHarness, grounded: Path
    ) -> None:
        result = planner.revise(grounded, encode(create_valid_draft()))

        assert result.code == 0, result.err
        assert result.out.startswith('stored revision 1 at ')
        assert result.out.splitlines()[1] == f'wrote {grounded.resolve().joinpath("plan.html")}'
        assert list_revision_files(grounded) == ['r1.json']

    def test_a_second_plan_is_stored_beside_the_first_as_revision_two(
        self, planner: PlanHarness, grounded: Path
    ) -> None:
        planner.revise(grounded, encode(create_valid_draft()))

        result = planner.revise_from_file(
            grounded, encode(replace(create_valid_draft(), intent='again'))
        )

        assert result.code == 0, result.err
        assert result.out.startswith('stored revision 2 at ')
        assert list_revision_files(grounded) == ['r1.json', 'r2.json']

    def test_a_plan_with_three_faults_is_refused_with_each_named_and_nothing_stored(
        self, planner: PlanHarness, grounded: Path
    ) -> None:
        faulty = plant_collision(plant_cycle(plant_groundless(create_valid_draft(), 2)), 0)

        result = planner.revise(grounded, encode(faulty))

        assert result.code == 1
        assert 'no revision was stored' in result.err
        assert 'ticket docs, acceptance 1 is required by nothing' in result.err
        assert 'in a cycle: loop-a -> loop-b -> loop-a' in result.err
        assert 'worktrees core and rogue can both change core/plans/' in result.err
        assert list_revision_files(grounded) == []
        assert not grounded.joinpath('plan.html').exists()

    def test_a_plan_that_is_not_json_is_refused_before_any_check(
        self, planner: PlanHarness, grounded: Path
    ) -> None:
        result = planner.revise(grounded, '{"intent": ')

        assert result.code == 1
        assert 'the plan cannot be read: it is not JSON' in result.err
        assert list_revision_files(grounded) == []
