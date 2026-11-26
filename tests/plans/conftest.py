"""Fixtures the plan concepts share: a real git repository with one committed file."""

from typing import TYPE_CHECKING

import pytest

from tests.casefile.ledger.builders import QUEUE_LINES, QUEUE_PATH
from tests.casefile.ledger.git_repository import create_empty_repository

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.ledger.git_repository import GitRepository


@pytest.fixture
def git_repository(tmp_path: Path) -> GitRepository:
    repository = create_empty_repository(tmp_path.joinpath('repo'))
    repository.write(QUEUE_PATH, ''.join(f'{line}\n' for line in QUEUE_LINES))
    repository.commit('add the queue')
    return repository
