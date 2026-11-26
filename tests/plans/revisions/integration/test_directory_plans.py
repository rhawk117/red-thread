"""DirectoryPlanRepository and DirectoryCaseShelf: a plan's files and the cases beside it."""

from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from msgspec.structs import replace
from red_thread_casefile.factory import CaseFiles
from red_thread_casefile.services import Framing
from red_thread_plans.domain import PLAN_HOME
from red_thread_plans.errors import CorruptPlanError, MissingPlanError, RevisionExistsError
from red_thread_plans.schemas import plan_from_text
from red_thread_plans.services import RevisionStamp
from red_thread_plans.store import DirectoryCaseShelf, DirectoryPlanRepository

from tests.casefile.ledger.builders import CASE_ID
from tests.casefile.ledger.memory import HEAD, MOMENT, FixedClock
from tests.plans.revisions.builders import PLAN_INDEX, create_valid_draft
from tests.plans.revisions.strategies import valid_plans

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_plans.domain import Plan, PlanDraft

    from tests.casefile.ledger.git_repository import GitRepository


def stamp(draft: PlanDraft, revision: int) -> Plan:
    return RevisionStamp(revision=revision, at=MOMENT, head=HEAD).apply(draft)


class TestDirectoryPlans:
    @pytest.fixture
    def plans(self, tmp_path: Path) -> DirectoryPlanRepository:
        return DirectoryPlanRepository(directory=tmp_path)

    def test_a_plan_without_revisions_reads_none(self, plans: DirectoryPlanRepository) -> None:
        assert plans.read_plans() == ()

    def test_a_revision_is_written_to_its_own_file_and_read_back_whole(
        self, plans: DirectoryPlanRepository
    ) -> None:
        plan = stamp(create_valid_draft(), 1)

        path = plans.add(plan)

        assert path == plans.directory.joinpath('r1.json')
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
            plans.directory.joinpath(stray).write_text('{}', encoding='utf-8')

        assert [plan.revision for plan in plans.read_plans()] == [1, 2, 9, 10]

    def test_a_corrupt_revision_is_named_by_its_path(self, plans: DirectoryPlanRepository) -> None:
        plans.add(stamp(create_valid_draft(), 1))
        broken = plans.directory.joinpath('r2.json')
        broken.write_text('{"revision": 2', encoding='utf-8')

        with pytest.raises(CorruptPlanError) as corrupt:
            plans.read_plans()

        assert corrupt.value.path == broken

    def test_the_index_is_written_beside_the_revisions_and_read_back(
        self, plans: DirectoryPlanRepository
    ) -> None:
        plans.write_index(PLAN_INDEX)

        assert plans.exists()
        assert plans.directory.joinpath('plan.json').is_file()
        assert plans.read_index() == PLAN_INDEX

    def test_a_directory_without_an_index_is_not_a_plan(
        self, plans: DirectoryPlanRepository
    ) -> None:
        with pytest.raises(MissingPlanError) as missing:
            plans.read_index()

        assert missing.value.path == plans.directory


def not_a_case_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        'case_id',
        [
            pytest.param('20261121-no-such-case', id='absent'),
            pytest.param('..', id='parent'),
            pytest.param(PLAN_HOME, id='plan-home'),
            pytest.param(f'../{CASE_ID}', id='climbing'),
        ],
    )


class TestDirectoryCaseShelf:
    framing = Framing(id=CASE_ID, target='why the queue stalls', kind='root-cause', bar='a line')

    @pytest.fixture
    def shelf(self, git_repository: GitRepository) -> DirectoryCaseShelf:
        state = git_repository.root.joinpath('.red-thread')
        CaseFiles(clock=FixedClock()).bind(state.joinpath(CASE_ID)).frame(self.framing)
        return DirectoryCaseShelf(state=state)

    def test_a_framed_case_is_found_with_its_ledger(self, shelf: DirectoryCaseShelf) -> None:
        record = shelf.find(CASE_ID)

        assert record is not None
        assert (record.case.id, record.ledger.entries) == (CASE_ID, ())

    @not_a_case_cases()
    def test_a_name_that_is_no_case_finds_nothing(
        self, shelf: DirectoryCaseShelf, case_id: str
    ) -> None:
        assert shelf.find(case_id) is None


class TestDirectoryPlanProperties:
    @given(plan=valid_plans)
    def test_any_stamped_plan_reads_back_equal(
        self, plan: PlanDraft, tmp_path_factory: pytest.TempPathFactory
    ) -> None:
        plans = DirectoryPlanRepository(directory=tmp_path_factory.mktemp('case'))
        stored = stamp(plan, 1)

        plans.add(stored)

        assert plans.read_plans() == (stored,)
