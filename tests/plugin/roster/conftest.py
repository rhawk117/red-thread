"""The roster hook of this repository."""

from typing import TYPE_CHECKING

import pytest

from tests.plugin.roster.hook import RosterHook

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def roster_hook(repository_root: Path) -> RosterHook:
    return RosterHook(root=repository_root)
