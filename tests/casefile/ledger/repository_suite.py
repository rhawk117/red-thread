"""The case repository contract, written once for the fake and the directory adapter."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.domain import LedgerSource
from red_thread_casefile.errors import CaseExistsError, CaseNotFoundError
from red_thread_casefile.store import CaseRepository

from tests.casefile.ledger.builders import create_case, create_finding
from tests.casefile.ledger.markdown import write_case_text, write_thread_text

if TYPE_CHECKING:
    from tests.casefile.ledger.markdown import TextSink


@dataclass(slots=True, kw_only=True, frozen=True)
class RepositoryHarness:
    repository: CaseRepository
    sink: TextSink

    def read_names(self) -> list[str]:
        return [source.name for source in self.repository.read()]


class CaseRepositoryContract:
    case_text = write_case_text(create_case())
    thread_text = write_thread_text((create_finding(finding_number=1),))

    class TestImplementation:
        def test_repository_satisfies_the_protocol(self, harness: RepositoryHarness) -> None:
            assert isinstance(harness.repository, CaseRepository)

    class TestBeforeTheCaseExists:
        def test_repository_reports_no_case(self, harness: RepositoryHarness) -> None:
            assert not harness.repository.exists()

        def test_reading_the_case_is_not_found(self, harness: RepositoryHarness) -> None:
            with pytest.raises(CaseNotFoundError):
                harness.repository.read()

    class TestCreate:
        def test_created_case_file_is_read_back_whole(self, harness: RepositoryHarness) -> None:
            harness.repository.create(CaseRepositoryContract.case_text)

            assert harness.repository.exists()
            assert harness.repository.read() == (
                LedgerSource(name='case.md', thread=None, text=CaseRepositoryContract.case_text),
            )

        def test_a_second_create_is_refused_and_keeps_the_first_text(
            self, harness: RepositoryHarness
        ) -> None:
            harness.repository.create(CaseRepositoryContract.case_text)

            with pytest.raises(CaseExistsError):
                harness.repository.create('---\n---\n')

            assert harness.repository.read()[0].text == CaseRepositoryContract.case_text

    class TestThreadFiles:
        @pytest.fixture
        def created(self, harness: RepositoryHarness) -> RepositoryHarness:
            harness.repository.create(CaseRepositoryContract.case_text)
            return harness

        def test_a_thread_file_follows_the_case_file_under_its_thread_name(
            self, created: RepositoryHarness
        ) -> None:
            created.sink.write('threads/T1.md', CaseRepositoryContract.thread_text)

            sources = created.repository.read()

            assert [source.thread for source in sources] == [None, 'T1']
            assert sources[1].text == CaseRepositoryContract.thread_text

        def test_threads_are_ordered_by_number_not_by_name(
            self, created: RepositoryHarness
        ) -> None:
            created.sink.write('threads/T10.md', CaseRepositoryContract.thread_text)
            created.sink.write('threads/T2.md', CaseRepositoryContract.thread_text)

            assert created.read_names() == ['case.md', 'threads/T2.md', 'threads/T10.md']

        def test_a_file_not_named_for_a_thread_comes_after_the_threads(
            self, created: RepositoryHarness
        ) -> None:
            created.sink.write('threads/notes.md', CaseRepositoryContract.thread_text)
            created.sink.write('threads/T3.md', CaseRepositoryContract.thread_text)

            assert created.read_names() == ['case.md', 'threads/T3.md', 'threads/notes.md']
