"""The case file over a real case directory, a real git repository and a fixed clock."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_casefile.services import Batch, CaseFile
from red_thread_casefile.store import DirectoryCaseRepository
from red_thread_core.store import GitSourceTree

from tests.casefile.ledger.builders import CASE_ID, create_case
from tests.casefile.ledger.memory import FixedClock

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_casefile.domain import Draft
    from red_thread_casefile.services import Added

    from tests.casefile.ledger.git_repository import GitRepository


@dataclass(slots=True, kw_only=True, frozen=True)
class DirectoryHarness:
    git: GitRepository
    directory: Path
    repository: DirectoryCaseRepository
    casefile: CaseFile

    @property
    def ledger_file(self) -> Path:
        return self.directory.joinpath('ledger.jsonl')

    def thread_file(self, thread: str) -> Path:
        return self.directory.joinpath('threads', f'{thread}.jsonl')

    def read_bytes(self, path: Path) -> bytes:
        return path.read_bytes() if path.is_file() else b''

    def add(self, *drafts: Draft, thread: str | None = None, round_number: int = 1) -> Added:
        return self.casefile.add(Batch(drafts=drafts, round=round_number, thread=thread))


def create_directory_harness(git: GitRepository) -> DirectoryHarness:
    directory = git.root.joinpath('.red-thread', CASE_ID)
    repository = DirectoryCaseRepository(directory=directory)
    casefile = CaseFile(
        repository=repository, tree=GitSourceTree(root=git.root), clock=FixedClock()
    )
    return DirectoryHarness(git=git, directory=directory, repository=repository, casefile=casefile)


def create_framed_directory_harness(git: GitRepository) -> DirectoryHarness:
    harness = create_directory_harness(git)
    harness.repository.create(create_case())
    return harness
