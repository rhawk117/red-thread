"""The case repository contract over a real case directory."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.store import DirectoryCaseRepository

from tests.casefile.ledger.directory import DirectorySink
from tests.casefile.ledger.repository_suite import RepositoryHarness

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def case_directory(tmp_path: Path) -> Path:
    return tmp_path.joinpath('.red-thread', '20261121-retry-queue-slowdown')


@pytest.fixture
def harness(case_directory: Path) -> RepositoryHarness:
    return RepositoryHarness(
        repository=DirectoryCaseRepository(directory=case_directory),
        sink=DirectorySink(directory=case_directory),
    )
