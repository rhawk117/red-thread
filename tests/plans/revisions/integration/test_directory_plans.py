"""DirectoryPlanRepository: a file per revision, created exclusively, read back in number order."""

from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from msgspec.structs import replace
from red_thread_plans.errors import CorruptPlanError, RevisionExistsError
from red_thread_plans.schemas import plan_from_text
from red_thread_plans.services import RevisionStamp
from red_thread_plans.store import DirectoryPlanRepository

from tests.casefile.ledger.memory import HEAD, MOMENT
from tests.plans.revisions.builders import create_valid_draft
from tests.plans.revisions.strategies import valid_plans

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_plans.domain import Plan, PlanDraft


def stamp(draft: PlanDraft, revision: int) -> Plan:
    return RevisionStamp(revision=revision, at=MOMENT, head=HEAD).apply(draft)


class TestDirectoryPlans:
    @pytest.fixture
    def plans(self, tmp_path: Path) -> DirectoryPlanRepository:
        return DirectoryPlanRepository(directory=tmp_path)

    def test_a_case_without_plans_reads_none(self, plans: DirectoryPlanRepository) -> None:
        assert plans.read_plans() == ()

    def test_a_revision_is_written_to_its_own_file_and_read_back_whole(
        self, plans: DirectoryPlanRepository
    ) -> None:
        plan = stamp(create_valid_draft(), 1)

        path = plans.add(plan)

        assert path == plans.folder.joinpath('r1.json')
        assert plan_from_text(path.read_text(encoding='utf-8')) == plan

    def test_a_stored_revision_is_never_overwritten(self, plans: DirectoryPlanRepository) -> None:
        path = plans.add(stamp(create_valid_draft(), 1))
        before = path.read_bytes()

        with pytest.raises(RevisionExistsError):
            plans.add(stamp(replace(create_valid_draft(), intent='another'), 1))

        assert path.read_bytes() == before

    def test_revisions_are_read_in_number_order_and_other_files_are_ignored(
        self, plans: DirectoryPlanRepository
    ) -> None:
        for revision in (10, 2, 1, 9):
            plans.add(stamp(create_valid_draft(), revision))
        for stray in ('notes.txt', 'r0.json', 'r01.json', 'r3.json.tmp'):
            plans.folder.joinpath(stray).write_text('{}', encoding='utf-8')

        assert [plan.revision for plan in plans.read_plans()] == [1, 2, 9, 10]

    def test_a_corrupt_revision_is_named_by_its_path(self, plans: DirectoryPlanRepository) -> None:
        plans.add(stamp(create_valid_draft(), 1))
        broken = plans.folder.joinpath('r2.json')
        broken.write_text('{"revision": 2', encoding='utf-8')

        with pytest.raises(CorruptPlanError) as corrupt:
            plans.read_plans()

        assert corrupt.value.path == broken


class TestDirectoryPlanProperties:
    @given(plan=valid_plans)
    def test_any_stamped_plan_reads_back_equal(
        self, plan: PlanDraft, tmp_path_factory: pytest.TempPathFactory
    ) -> None:
        plans = DirectoryPlanRepository(directory=tmp_path_factory.mktemp('case'))
        stored = stamp(plan, 1)

        plans.add(stored)

        assert plans.read_plans() == (stored,)
