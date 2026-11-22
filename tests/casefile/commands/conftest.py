"""The command line harness over a real git repository."""

from typing import TYPE_CHECKING

import pytest

from tests.casefile.commands.cli import CliHarness

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.ledger.git_repository import GitRepository


@pytest.fixture
def cli(
    git_repository: GitRepository,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> CliHarness:
    return CliHarness(git=git_repository, capsys=capsys, monkeypatch=monkeypatch)


@pytest.fixture
def case(cli: CliHarness) -> Path:
    return cli.init()
