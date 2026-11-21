"""Fixtures the casefile concepts share: memory harnesses and a real git repository."""

from typing import TYPE_CHECKING

import pytest

from tests.casefile.ledger.builders import (
    QUEUE_LINES,
    QUEUE_PATH,
    create_case_harness,
    create_framed_harness,
)
from tests.casefile.ledger.directory import (
    create_directory_harness,
    create_framed_directory_harness,
)
from tests.casefile.ledger.git_repository import create_empty_repository
from tests.casefile.lenses.builders import (
    create_directory_press_harness,
    create_press_harness,
)

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.ledger.builders import CaseHarness
    from tests.casefile.ledger.directory import DirectoryHarness
    from tests.casefile.ledger.git_repository import GitRepository
    from tests.casefile.lenses.builders import DirectoryPressHarness, PressHarness


@pytest.fixture
def case_harness() -> CaseHarness:
    return create_case_harness()


@pytest.fixture
def framed_harness() -> CaseHarness:
    return create_framed_harness()


@pytest.fixture
def empty_repository(tmp_path: Path) -> GitRepository:
    return create_empty_repository(tmp_path.joinpath('repo'))


@pytest.fixture
def git_repository(empty_repository: GitRepository) -> GitRepository:
    empty_repository.write(QUEUE_PATH, ''.join(f'{line}\n' for line in QUEUE_LINES))
    empty_repository.commit('add the queue')
    return empty_repository


@pytest.fixture
def directory_harness(git_repository: GitRepository) -> DirectoryHarness:
    return create_directory_harness(git_repository)


@pytest.fixture
def framed_directory_harness(git_repository: GitRepository) -> DirectoryHarness:
    return create_framed_directory_harness(git_repository)


@pytest.fixture
def press_harness() -> PressHarness:
    return create_press_harness()


@pytest.fixture
def directory_press_harness(git_repository: GitRepository) -> DirectoryPressHarness:
    return create_directory_press_harness(git_repository)
