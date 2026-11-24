"""The case repository contract, written once for the fake and the directory adapter."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from msgspec.structs import replace
from red_thread_casefile.domain import Capabilities
from red_thread_casefile.errors import CaseNotFoundError
from red_thread_casefile.store import CaseRepository

from tests.casefile.ledger.builders import URL_CITE, create_case, create_entry

if TYPE_CHECKING:
    from red_thread_casefile.domain import Entry


@dataclass(slots=True, kw_only=True, frozen=True)
class RepositoryHarness:
    repository: CaseRepository


class CaseRepositoryContract:
    full_entry = create_entry(
        seq=1,
        kind='known',
        text='the sleep blocks the queue',
        source='scout',
        round_number=2,
        verdict='VERIFIED',
        cite='src/queue.py:3',
        quote='time.sleep(job.delay)',
        addr='src/queue.py#retry',
        rests_on='a docs page for another version',
        refute='the stall ends when the sleep is removed',
        supersedes=('e0',),
    )

    class TestImplementation:
        def test_repository_satisfies_the_protocol(self, harness: RepositoryHarness) -> None:
            assert isinstance(harness.repository, CaseRepository)

    class TestBeforeTheCaseExists:
        def test_repository_reports_no_case(self, harness: RepositoryHarness) -> None:
            assert not harness.repository.exists()

        def test_reading_the_case_is_not_found(self, harness: RepositoryHarness) -> None:
            with pytest.raises(CaseNotFoundError):
                harness.repository.read_case()

        def test_reading_the_ledger_is_not_found(self, harness: RepositoryHarness) -> None:
            with pytest.raises(CaseNotFoundError):
                harness.repository.read_ledger()

    class TestCase:
        full_case = replace(
            create_case(),
            publish=True,
            page_url='https://claude.ai/artifact/retry-queue',
            capabilities=Capabilities(languages=('Python', 'Go')),
        )

        def test_created_case_is_read_back_whole(self, harness: RepositoryHarness) -> None:
            harness.repository.create(self.full_case)

            assert harness.repository.exists()
            assert harness.repository.read_case() == self.full_case

        def test_written_case_replaces_the_created_one(self, harness: RepositoryHarness) -> None:
            harness.repository.create(create_case())
            harness.repository.write_case(self.full_case)

            assert harness.repository.read_case() == self.full_case

        def test_new_case_has_an_empty_ledger(self, harness: RepositoryHarness) -> None:
            harness.repository.create(create_case())

            assert harness.repository.read_ledger().entries == ()

    class TestAppend:
        @pytest.fixture
        def created(self, harness: RepositoryHarness) -> RepositoryHarness:
            harness.repository.create(create_case())
            return harness

        def read_refs(self, harness: RepositoryHarness) -> list[str]:
            return [entry.ref for entry in harness.repository.read_ledger().entries]

        def test_entry_with_every_field_is_read_back_equal(
            self, created: RepositoryHarness
        ) -> None:
            created.repository.append(None, (CaseRepositoryContract.full_entry,))

            assert created.repository.read_ledger().entries == (CaseRepositoryContract.full_entry,)

        def test_entry_with_only_required_fields_is_read_back_equal(
            self, created: RepositoryHarness
        ) -> None:
            bare = create_entry(seq=1, head=None)
            created.repository.append(None, (bare,))

            assert created.repository.read_ledger().entries == (bare,)

        def test_later_append_follows_the_earlier_one(self, created: RepositoryHarness) -> None:
            first = create_entry(seq=1)
            second = create_entry(seq=2, cite=URL_CITE, kind='known', verdict='VERIFIED')
            third = create_entry(seq=3)
            created.repository.append(None, (first, second))
            created.repository.append(None, (third,))

            assert created.repository.read_ledger().entries == (first, second, third)

        def test_thread_entries_carry_their_thread(self, created: RepositoryHarness) -> None:
            created.repository.append('T1', (create_entry(seq=1), create_entry(seq=2)))
            created.repository.append(None, (create_entry(seq=1),))

            refs = self.read_refs(created)

            assert sorted(refs) == ['T1.e1', 'T1.e2', 'e1']

        def test_each_file_keeps_its_own_entries(self, created: RepositoryHarness) -> None:
            primary: Entry = create_entry(seq=1, text='written by the primary')
            lead: Entry = create_entry(seq=1, text='written by a lead', thread='T1')
            created.repository.append(None, (primary,))
            created.repository.append('T1', (lead,))

            entries = created.repository.read_ledger().entries

            assert set(entries) == {primary, lead}
            assert created.repository.read_ledger().count_in(None) == 1
            assert created.repository.read_ledger().count_in('T1') == 1

        def test_threads_are_ordered_by_number_not_by_name(
            self, created: RepositoryHarness
        ) -> None:
            created.repository.append('T10', (create_entry(seq=1),))
            created.repository.append('T2', (create_entry(seq=1),))

            assert created.repository.read_ledger().threads == ('T2', 'T10')
