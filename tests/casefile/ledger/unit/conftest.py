"""The case repository contract over the in-memory fake."""

import pytest

from tests.casefile.ledger.memory import MemoryCaseRepository
from tests.casefile.ledger.repository_suite import RepositoryHarness


@pytest.fixture
def harness() -> RepositoryHarness:
    repository = MemoryCaseRepository()
    return RepositoryHarness(repository=repository, sink=repository)
