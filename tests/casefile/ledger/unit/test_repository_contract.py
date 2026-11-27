"""The case repository contract against the in-memory fake."""

from red_thread_casefile.store import CaseRepository
from red_thread_core.store import SourceTree
from red_thread_core.timekeeping import Clock

from tests.casefile.ledger.memory import MemoryCaseRepository, MemorySourceTree
from tests.casefile.ledger.repository_suite import CaseRepositoryContract
from tests.core.timekeeping.clock import FixedClock


class TestMemoryCaseRepository(CaseRepositoryContract):
    pass


class TestMemoryImplementations:
    def test_fakes_satisfy_their_protocols(self) -> None:
        assert isinstance(MemoryCaseRepository(), CaseRepository)
        assert isinstance(MemorySourceTree(), SourceTree)
        assert isinstance(FixedClock(), Clock)
