"""The case repository contract against the in-memory fake."""

from red_thread_casefile.store import CaseRepository
from red_thread_core.store import Clock, SourceTree

from tests.casefile.ledger.memory import (
    FixedClock,
    MemoryCaseRepository,
    MemorySourceTree,
)
from tests.casefile.ledger.repository_suite import CaseRepositoryContract


class TestMemoryCaseRepository(CaseRepositoryContract):
    pass


class TestMemoryImplementations:
    def test_fakes_satisfy_their_protocols(self) -> None:
        assert isinstance(MemoryCaseRepository(), CaseRepository)
        assert isinstance(MemorySourceTree(), SourceTree)
        assert isinstance(FixedClock(), Clock)
