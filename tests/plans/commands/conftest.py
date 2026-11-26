"""The case file and plan command lines over one real git repository."""

from typing import TYPE_CHECKING

import pytest

from tests.casefile.commands.cli import CliHarness
from tests.plans.commands.cli import PlanHarness

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


@pytest.fixture
def planner(
    git_repository: GitRepository,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> PlanHarness:
    return PlanHarness(scratch=git_repository.root.parent, capsys=capsys, monkeypatch=monkeypatch)
