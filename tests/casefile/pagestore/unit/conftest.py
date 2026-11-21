"""The page store contract over the in-memory fake."""

import pytest

from tests.casefile.ledger.memory import MemoryPageStore
from tests.casefile.pagestore.page_store_suite import PageHarness


@pytest.fixture
def harness() -> PageHarness:
    store = MemoryPageStore()
    return PageHarness(store=store, reader=store)
