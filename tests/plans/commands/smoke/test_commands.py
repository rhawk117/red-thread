"""redthread-plan init, revise and render, driven through main(argv) in a git repository."""

from typing import TYPE_CHECKING

import msgspec
import pytest
from msgspec.structs import replace
from red_thread_plans.schemas import index_from_text

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


def list_revision_files(plan: Path) -> list[str]:
    return sorted(path.name for path in plan.glob('r*.json'))


@pytest.fixture
def grounded(cli: CliHarness, case: Path) -> Path:
    added = cli.add(case, KNOWN, DECISION)
    assert added.code == 0, added.err
    return case


@pytest.fixture
def plan(cli: CliHarness, planner: PlanHarness) -> Path:
    return planner.init(cli.git.root)


class TestInit:
    def test_a_plan_is_created_beside_the_cases_with_an_index(
        self, cli: CliHarness, plan: Path
    ) -> None:
        index = index_from_text(plan.joinpath('plan.json').read_text(encoding='utf-8'))

        assert plan.parent == cli.git.root.joinpath('.red-thread', 'plans').resolve()
        assert (index.id, index.title, index.cases) == (plan.name, 'give a case a plan', ())

    def test_a_second_init_with_the_same_title_is_refused(
        self, cli: CliHarness, planner: PlanHarness, plan: Path
    ) -> None:
        result = planner.run('init', '--root', str(cli.git.root), '--title', 'give a case a plan')

        assert result.code == 1
        assert f'plan {plan.name} already exists' in result.err


class TestRevise:
    def test_a_sound_plan_is_stored_as_revision_one_and_reported(
        self, planner: PlanHarness, grounded: Path, plan: Path
    ) -> None:
        result = planner.revise(plan, encode(create_valid_draft(grounded.name)))

        assert result.code == 0, result.err
        assert result.out.startswith('stored revision 1 at ')
        assert result.out.splitlines()[1] == f'wrote {plan.joinpath("plan.html")}'
        assert list_revision_files(plan) == ['r1.json']

    def test_a_stored_plan_lists_its_case_in_the_index(
        self, planner: PlanHarness, grounded: Path, plan: Path
    ) -> None:
        planner.revise(plan, encode(create_valid_draft(grounded.name)))

        index = index_from_text(plan.joinpath('plan.json').read_text(encoding='utf-8'))

        assert index.cases == (grounded.name,)

    def test_a_second_plan_is_stored_beside_the_first_as_revision_two(
        self, planner: PlanHarness, grounded: Path, plan: Path
    ) -> None:
        draft = create_valid_draft(grounded.name)
        planner.revise(plan, encode(draft))

        result = planner.revise_from_file(plan, encode(replace(draft, intent='again')))

        assert result.code == 0, result.err
        assert result.out.startswith('stored revision 2 at ')
        assert list_revision_files(plan) == ['r1.json', 'r2.json']

    def test_a_plan_with_three_faults_is_refused_with_each_named_and_nothing_stored(
        self, planner: PlanHarness, grounded: Path, plan: Path
    ) -> None:
        sound = create_valid_draft(grounded.name)
        faulty = plant_collision(plant_cycle(plant_groundless(sound, 2)), 0)

        result = planner.revise(plan, encode(faulty))

        assert result.code == 1
        assert 'no revision was stored' in result.err
        assert 'ticket docs, acceptance 1 is required by nothing' in result.err
        assert 'in a cycle: loop-a -> loop-b -> loop-a' in result.err
        assert 'worktrees core and rogue can both change core/plans/' in result.err
        assert list_revision_files(plan) == []
        assert not plan.joinpath('plan.html').exists()

    def test_a_plan_that_is_not_json_is_refused_before_any_check(
        self, planner: PlanHarness, plan: Path
    ) -> None:
        result = planner.revise(plan, '{"intent": ')

        assert result.code == 1
        assert 'the plan cannot be read: it is not JSON' in result.err
        assert list_revision_files(plan) == []


class TestRender:
    def test_render_redraws_the_plan_page(
        self, planner: PlanHarness, grounded: Path, plan: Path
    ) -> None:
        planner.revise(plan, encode(create_valid_draft(grounded.name)))
        plan.joinpath('plan.html').unlink()

        result = planner.render(plan)

        assert result.code == 0, result.err
        assert result.out == f'wrote {plan.joinpath("plan.html")}\n'
        assert plan.joinpath('plan.html').is_file()

    def test_render_before_any_revision_is_refused(self, planner: PlanHarness, plan: Path) -> None:
        result = planner.render(plan)

        assert result.code == 1
        assert 'has no revision yet' in result.err
