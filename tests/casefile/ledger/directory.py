"""The case file over a real case directory, a real git repository and a fixed clock."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_casefile.domain import CASE_FILE
from red_thread_casefile.packaged import load_wording
from red_thread_casefile.services import CaseFile
from red_thread_casefile.store import DirectoryCaseRepository
from red_thread_core.store import GitSourceTree

from tests.casefile.ledger.builders import CASE_ID, create_case
from tests.casefile.ledger.markdown import CaseScribe, name_file, write_case_text
from tests.codec import YAML
from tests.core.timekeeping.clock import FixedClock

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_casefile.domain import Case, CaseFinding
    from red_thread_casefile.services import Checked

    from tests.casefile.ledger.git_repository import GitRepository


@dataclass(slots=True, kw_only=True, frozen=True)
class DirectorySink:
    directory: Path

    def write(self, name: str, text: str) -> None:
        path = self.directory.joinpath(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')


@dataclass(slots=True, kw_only=True, frozen=True)
class DirectoryHarness:
    git: GitRepository
    directory: Path
    repository: DirectoryCaseRepository
    casefile: CaseFile
    scribe: CaseScribe

    @property
    def case_file(self) -> Path:
        return self.directory.joinpath(CASE_FILE)

    def thread_file(self, thread: str) -> Path:
        return self.directory.joinpath(name_file(thread))

    def read_bytes(self, path: Path) -> bytes:
        return path.read_bytes() if path.is_file() else b''

    def seed(self, thread: str | None, *findings: CaseFinding) -> None:
        self.scribe.seed(thread, *findings)

    def frame(self, case: Case) -> None:
        self.scribe.frame(case)

    def check(self) -> Checked:
        return self.casefile.check()


def create_directory_harness(git: GitRepository) -> DirectoryHarness:
    directory = git.root.joinpath('.red-thread', CASE_ID)
    repository = DirectoryCaseRepository(directory=directory)
    casefile = CaseFile(
        repository=repository,
        tree=GitSourceTree(root=git.root),
        clock=FixedClock(),
        wording=load_wording(),
        codec=YAML,
    )
    scribe = CaseScribe(sink=DirectorySink(directory=directory), cases=[create_case()])
    return DirectoryHarness(
        git=git, directory=directory, repository=repository, casefile=casefile, scribe=scribe
    )


def create_framed_directory_harness(git: GitRepository) -> DirectoryHarness:
    harness = create_directory_harness(git)
    harness.repository.create(write_case_text(create_case()))
    return harness
