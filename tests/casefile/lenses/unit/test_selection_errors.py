"""export: a selection that names no live entry raises and writes nothing."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.errors import UnknownSelectionRefError
from red_thread_casefile.lenses import Selection

from tests.casefile.ledger.builders import create_entry
from tests.casefile.lenses.builders import create_numbered_entries, export
from tests.params import as_params

if TYPE_CHECKING:
    from tests.casefile.lenses.builders import PressHarness

PREVIOUS = 'a brief written by an earlier export\n'


@dataclass(slots=True, kw_only=True, frozen=True)
class RefScenario:
    name: str
    selection: Selection
    unknown: str
    marks: tuple[pytest.MarkDecorator, ...] = ()


def selection_ref_cases() -> pytest.MarkDecorator:
    scenarios = [
        RefScenario(
            name='include-never-existed', selection=Selection(include=('e99',)), unknown='e99'
        ),
        RefScenario(
            name='blocking-never-existed', selection=Selection(blocking=('e99',)), unknown='e99'
        ),
        RefScenario(
            name='include-names-a-retired-entry', selection=Selection(include=('e1',)), unknown='e1'
        ),
        RefScenario(
            name='blocking-names-a-retired-entry',
            selection=Selection(blocking=('e1',)),
            unknown='e1',
        ),
        RefScenario(
            name='thread-ref-in-no-thread', selection=Selection(include=('T1.e1',)), unknown='T1.e1'
        ),
        RefScenario(
            name='live-refs-then-one-unknown',
            selection=Selection(include=('e2', 'e3', 'e99')),
            unknown='e99',
        ),
        RefScenario(
            name='unknown-blocking-beside-valid-include',
            selection=Selection(include=('e2',), blocking=('e77',)),
            unknown='e77',
        ),
    ]
    return pytest.mark.parametrize('scenario', as_params(scenarios))


class TestUnknownSelectionRef:
    @pytest.fixture
    def harness(self, press_harness: PressHarness) -> PressHarness:
        press_harness.seed(
            *create_numbered_entries('known', 1),
            create_entry(seq=2, kind='known', text='the replacement', supersedes=('e1',)),
            *create_numbered_entries('open', 1, start=3),
        )
        press_harness.pages.write('out/brief.md', PREVIOUS)
        return press_harness

    def assert_refused_without_writing(
        self, harness: PressHarness, selection: Selection, *, html: bool = False
    ) -> UnknownSelectionRefError:
        before = harness.snapshot()
        with pytest.raises(UnknownSelectionRefError) as raised:
            export(harness, 'brief', selection, html=html)
        assert harness.snapshot() == before
        return raised.value

    @selection_ref_cases()
    def test_a_ref_that_is_unknown_or_retired_raises_and_writes_nothing(
        self, harness: PressHarness, scenario: RefScenario
    ) -> None:
        error = self.assert_refused_without_writing(harness, scenario.selection)

        assert error.ref == scenario.unknown

    def test_the_html_page_is_not_written_either(self, harness: PressHarness) -> None:
        self.assert_refused_without_writing(harness, Selection(include=('e99',)), html=True)

        assert 'out/brief.html' not in harness.pages.files

    def test_a_selection_naming_only_live_entries_exports(self, harness: PressHarness) -> None:
        export(harness, 'brief', Selection(include=('e2', 'e3'), blocking=('e3',)))

        assert harness.read_markdown('brief') != PREVIOUS
