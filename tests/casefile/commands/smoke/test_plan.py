"""casefile plan, driven through main(argv) against a temporary git repository."""

from typing import TYPE_CHECKING

import msgspec
import pytest
from msgspec.structs import replace

from tests.casefile.ledger.builders import KNOWN
from tests.casefile.plans.builders import (
    create_valid_draft,
    plant_collision,
    plant_cycle,
    plant_groundless,
)

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_casefile.plans.domain import PlanDraft

    from tests.casefile.commands.cli import CliHarness, CliRun

DECISION = {'kind': 'decision', 'text': 'keep one writer', 'source': 'user'}


def encode(draft: PlanDraft) -> str:
    return msgspec.json.encode(draft).decode()


def list_revision_files(case: Path) -> list[str]:
    return sorted(path.name for path in case.joinpath('plans').glob('*'))


class TestPlan:
    def send(self, cli: CliHarness, case: Path, text: str) -> CliRun:
        return cli.run('plan', '--case', str(case), stdin=text)

    def send_file(self, cli: CliHarness, case: Path, text: str) -> CliRun:
        plan_file = cli.git.root.parent.joinpath('plan.json')
        plan_file.write_text(text, encoding='utf-8')
        return cli.run('plan', '--case', str(case), '--file', str(plan_file))

    @pytest.fixture
    def grounded(self, cli: CliHarness, case: Path) -> Path:
        added = cli.add(case, KNOWN, DECISION)
        assert added.code == 0, added.err
        return case

    def test_a_sound_plan_is_stored_as_revision_one_and_reported(
        self, cli: CliHarness, grounded: Path
    ) -> None:
        result = self.send(cli, grounded, encode(create_valid_draft()))

        assert result.code == 0, result.err
        assert result.out.startswith('stored revision 1 at ')
        assert list_revision_files(grounded) == ['r1.json']

    def test_a_second_plan_is_stored_beside_the_first_as_revision_two(
        self, cli: CliHarness, grounded: Path
    ) -> None:
        self.send(cli, grounded, encode(create_valid_draft()))

        result = self.send_file(
            cli, grounded, encode(replace(create_valid_draft(), intent='again'))
        )

        assert result.code == 0, result.err
        assert result.out.startswith('stored revision 2 at ')
        assert list_revision_files(grounded) == ['r1.json', 'r2.json']

    def test_a_plan_with_three_faults_is_refused_with_each_named_and_nothing_stored(
        self, cli: CliHarness, grounded: Path
    ) -> None:
        faulty = plant_collision(plant_cycle(plant_groundless(create_valid_draft(), 2)), 0)

        result = self.send(cli, grounded, encode(faulty))

        assert result.code == 1
        assert 'no revision was stored' in result.err
        assert 'ticket docs, acceptance 1 rests on nothing' in result.err
        assert 'in a cycle: loop-a -> loop-b -> loop-a' in result.err
        assert 'lanes core and rogue can both change core/plans/' in result.err
        assert list_revision_files(grounded) == []

    def test_a_plan_that_is_not_json_is_refused_before_any_check(
        self, cli: CliHarness, grounded: Path
    ) -> None:
        result = self.send(cli, grounded, '{"intent": ')

        assert result.code == 1
        assert 'the plan cannot be read: it is not JSON' in result.err
        assert list_revision_files(grounded) == []
