"""redthread-plan init and check, driven through main(argv) in a git repository."""

from typing import TYPE_CHECKING

import pytest

from tests.casefile.ledger.builders import KNOWN
from tests.plans.document.builders import (
    CRITERION,
    SOUND_SECTIONS,
    TITLE,
    edit_plan,
    fill_plan,
    find_line_number,
)

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.commands.cli import CliHarness, CliRun
    from tests.plans.commands.cli import PlanHarness

DECISION = {'kind': 'decision', 'text': 'cap each job at five attempts', 'source': 'user'}


def list_state(root: Path) -> list[str]:
    state = root.joinpath('.red-thread')
    return sorted(str(path.relative_to(state)) for path in state.rglob('*'))


@pytest.fixture
def grounded(cli: CliHarness, case: Path) -> Path:
    cli.write(case, KNOWN, DECISION)
    return case


@pytest.fixture
def plan(planner: PlanHarness, grounded: Path) -> Path:
    return planner.open(grounded.name)


class TestInit:
    def test_the_plan_sits_under_tickets_with_its_case_as_c1(
        self, planner: PlanHarness, grounded: Path, plan: Path
    ) -> None:
        text = plan.read_text(encoding='utf-8')

        assert plan.parent.parent == planner.root.joinpath('.red-thread', 'tickets').resolve()
        assert plan.name == 'plan.md'
        assert text.startswith(f'---\nid: {plan.parent.name}\ntitle: {TITLE}\nstatus: draft\n')
        assert f'  C1: {grounded.name}\n' in text

    def test_a_plan_with_no_case_is_refused(self, planner: PlanHarness) -> None:
        result = planner.init()

        assert result.code == 1
        assert 'the plan names no case' in result.err

    def test_a_plan_on_an_unknown_case_is_refused_and_nothing_written(
        self, planner: PlanHarness, grounded: Path
    ) -> None:
        before = list_state(planner.root)

        result = planner.init(grounded.name, '20261126-no-such-case')

        assert result.code == 1
        assert 'case 20261126-no-such-case is not under .red-thread/' in result.err
        assert list_state(planner.root) == before

    @pytest.mark.usefixtures('plan')
    def test_a_second_plan_with_the_same_id_is_refused(
        self, planner: PlanHarness, grounded: Path
    ) -> None:
        result = planner.init(grounded.name)

        assert result.code == 1
        assert 'already exists' in result.err


class TestCheck:
    @pytest.fixture
    def written(self, plan: Path) -> Path:
        plan.write_text(fill_plan(plan.read_text(encoding='utf-8'), SOUND_SECTIONS), 'utf-8')
        return plan

    def check_edited(self, planner: PlanHarness, plan: Path, *edits: tuple[str, str]) -> CliRun:
        plan.write_text(edit_plan(plan.read_text(encoding='utf-8'), edits), 'utf-8')
        return planner.check(plan)

    def test_a_written_plan_passes_and_counts_its_grounds(
        self, planner: PlanHarness, written: Path
    ) -> None:
        result = planner.check(written)

        assert result.code == 0, result.err
        assert result.out == f'checked {written}: 1 criteria rest on 2 findings\n'

    def test_the_directory_of_a_plan_is_checked_as_its_plan(
        self, planner: PlanHarness, written: Path
    ) -> None:
        assert planner.check(written.parent).code == 0

    def test_a_fresh_plan_names_each_empty_section(self, planner: PlanHarness, plan: Path) -> None:
        result = planner.check(plan)

        assert result.code == 1
        assert all(f'"## {title}" is empty' in result.err for title in ('Intent', 'Tasks'))

    def test_an_unfit_finding_id_is_named_with_its_line(
        self, planner: PlanHarness, written: Path
    ) -> None:
        edited = CRITERION.replace('C1.e2', 'C1.e9')
        result = self.check_edited(planner, written, (CRITERION, edited))
        line = find_line_number(written.read_text(encoding='utf-8'), edited)

        assert result.code == 1
        assert f'line {line}: C1.e9 is not a finding of its case' in result.err

    def test_a_bare_lights_value_is_refused_with_the_quotes_to_add(
        self, planner: PlanHarness, written: Path
    ) -> None:
        result = self.check_edited(planner, written, ('lights: null', 'lights: on'))

        assert result.code == 1
        assert 'write lights: "on" or lights: "off" with the quotes' in result.err

    def test_check_writes_nothing(self, planner: PlanHarness, written: Path) -> None:
        before = written.read_bytes()

        planner.check(written)

        assert written.read_bytes() == before
