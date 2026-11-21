"""The page store contract over a real directory."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.store import DirectoryPageStore

from tests.casefile.pagestore.directory import DirectoryPageReader
from tests.casefile.pagestore.page_store_suite import PageHarness

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def case_directory(tmp_path: Path) -> Path:
    return tmp_path.joinpath('.red-thread', '20261121-retry-queue-slowdown')


@pytest.fixture
def harness(case_directory: Path) -> PageHarness:
    return PageHarness(
        store=DirectoryPageStore(directory=case_directory),
        reader=DirectoryPageReader(directory=case_directory),
    )
