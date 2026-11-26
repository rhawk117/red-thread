"""A press over the in-memory case file and page store, and one over a real case directory."""

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from red_thread_casefile.factory import CaseFiles
from red_thread_casefile.lenses import Selection
from red_thread_casefile.packaged import load_lens_book
from red_thread_casefile.services import ExportRequest, Press

from tests.casefile.ledger.builders import QUEUE_PATH, create_entry, create_framed_harness
from tests.casefile.ledger.directory import create_framed_directory_harness
from tests.casefile.ledger.memory import FixedClock, MemoryPageStore
from tests.casefile.lenses.cases import QUEUE_CITE, QUEUE_QUOTE

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_casefile.domain import Case, Entry, EntryKind
    from red_thread_casefile.lenses import LensName
    from red_thread_casefile.services import Exported

    from tests.casefile.ledger.builders import CaseHarness
    from tests.casefile.ledger.directory import DirectoryHarness
    from tests.casefile.ledger.git_repository import GitRepository
    from tests.casefile.lenses.cases import FlagScenario


def create_numbered_entries(
    kind: EntryKind, count: int, *, start: int = 1, thread: str | None = None
) -> tuple[Entry, ...]:
    return tuple(
        create_entry(seq=seq, kind=kind, thread=thread, text=f'{kind} number {seq}')
        for seq in range(start, start + count)
    )


FLAGGED_TEXT = 'the sleep blocks the queue'


@runtime_checkable
class Pressing(Protocol):
    @property
    def press(self) -> Press: ...


def export(
    harness: Pressing, lens: LensName, selection: Selection | None = None, *, html: bool = False
) -> Exported:
    request = ExportRequest(lens=lens, selection=selection or Selection(), html=html)
    return harness.press.export(request)


@dataclass(slots=True, kw_only=True, frozen=True)
class PressHarness:
    case: CaseHarness
    pages: MemoryPageStore
    press: Press

    def seed(self, *entries: Entry) -> None:
        self.case.seed(None, *entries)

    def seed_thread(self, thread: str, *entries: Entry) -> None:
        self.case.seed(thread, *entries)

    def frame(self, case: Case) -> None:
        self.case.repository.write_case(case)

    def export_markdown(self, lens: LensName, selection: Selection | None = None) -> str:
        export(self, lens, selection)
        return self.read_markdown(lens)

    def read_markdown(self, lens: LensName) -> str:
        return self.pages.files[f'out/{lens}.md']

    def read_page(self, lens: LensName) -> str:
        return self.pages.files[f'out/{lens}.html']

    def snapshot(self) -> dict[str, str]:
        return dict(self.pages.files)


def create_press_harness() -> PressHarness:
    case = create_framed_harness()
    pages = MemoryPageStore()
    return PressHarness(
        case=case,
        pages=pages,
        press=Press(record=case.casefile, pages=pages, book=load_lens_book()),
    )


def seed_flag_scenario(harness: PressHarness, scenario: FlagScenario) -> None:
    cited = create_entry(
        seq=1,
        kind='known',
        text=FLAGGED_TEXT,
        cite=QUEUE_CITE,
        quote=QUEUE_QUOTE,
        head=scenario.entry_head,
    )
    harness.seed(cited)
    harness.case.tree.advance(scenario.tree_head)
    if scenario.tree_lines is None:
        harness.case.tree.remove(QUEUE_PATH)
        return

    harness.case.tree.write(QUEUE_PATH, scenario.tree_lines)


@dataclass(slots=True, kw_only=True, frozen=True)
class DirectoryPressHarness:
    directory: DirectoryHarness
    press: Press

    @property
    def case_directory(self) -> Path:
        return self.directory.directory

    def out_file(self, name: str) -> Path:
        return self.case_directory.joinpath(name)

    def read_case_record(self) -> dict[str, object]:
        text = self.out_file('case.json').read_text(encoding='utf-8')
        record: dict[str, object] = json.loads(text)
        return record


def create_directory_press_harness(git: GitRepository) -> DirectoryPressHarness:
    directory = create_framed_directory_harness(git)
    press = CaseFiles(clock=FixedClock()).open_press(directory.directory)
    return DirectoryPressHarness(directory=directory, press=press)
