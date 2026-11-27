"""export: a selection that names no live finding raises and writes nothing."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.errors import UnknownSelectedFindingError
from red_thread_casefile.lenses import Selection

from tests.casefile.ledger.builders import create_finding
from tests.casefile.lenses.builders import create_numbered_findings, export
from tests.params import as_params

if TYPE_CHECKING:
    from tests.casefile.lenses.builders import PressHarness

PREVIOUS = 'a brief written by an earlier export\n'


@dataclass(slots=True, kw_only=True, frozen=True)
class UnknownFindingScenario:
    name: str
    selection: Selection
    unknown: str
    marks: tuple[pytest.MarkDecorator, ...] = ()


def selection_finding_id_cases() -> pytest.MarkDecorator:
    scenarios = [
        UnknownFindingScenario(
            name='include-never-existed', selection=Selection(include=('e99',)), unknown='e99'
        ),
        UnknownFindingScenario(
            name='blocking-never-existed', selection=Selection(blocking=('e99',)), unknown='e99'
        ),
        UnknownFindingScenario(
            name='include-names-a-retired-finding',
            selection=Selection(include=('e1',)),
            unknown='e1',
        ),
        UnknownFindingScenario(
            name='blocking-names-a-retired-finding',
            selection=Selection(blocking=('e1',)),
            unknown='e1',
        ),
        UnknownFindingScenario(
            name='thread-finding-id-in-no-thread',
            selection=Selection(include=('T1.e1',)),
            unknown='T1.e1',
        ),
        UnknownFindingScenario(
            name='live-finding-ids-then-one-unknown',
            selection=Selection(include=('e2', 'e3', 'e99')),
            unknown='e99',
        ),
        UnknownFindingScenario(
            name='unknown-blocking-beside-valid-include',
            selection=Selection(include=('e2',), blocking=('e77',)),
            unknown='e77',
        ),
    ]
    return pytest.mark.parametrize('scenario', as_params(scenarios))


class TestUnknownSelectedFinding:
    @pytest.fixture
    def harness(self, press_harness: PressHarness) -> PressHarness:
        press_harness.seed(
            *create_numbered_findings('known', 1),
            create_finding(
                finding_number=2, kind='known', text='the replacement', supersedes=('e1',)
            ),
            *create_numbered_findings('open', 1, start=3),
        )
        press_harness.pages.write('out/brief.md', PREVIOUS)
        return press_harness

    def assert_refused_without_writing(
        self, harness: PressHarness, selection: Selection, *, html: bool = False
    ) -> UnknownSelectedFindingError:
        before = harness.snapshot()
        with pytest.raises(UnknownSelectedFindingError) as raised:
            export(harness, 'brief', selection, html=html)
        assert harness.snapshot() == before
        return raised.value

    @selection_finding_id_cases()
    def test_a_finding_id_that_is_unknown_or_retired_raises_and_writes_nothing(
        self, harness: PressHarness, scenario: UnknownFindingScenario
    ) -> None:
        error = self.assert_refused_without_writing(harness, scenario.selection)

        assert error.finding_id == scenario.unknown

    def test_the_html_page_is_not_written_either(self, harness: PressHarness) -> None:
        self.assert_refused_without_writing(harness, Selection(include=('e99',)), html=True)

        assert 'out/brief.html' not in harness.pages.files

    def test_a_selection_naming_only_live_findings_exports(self, harness: PressHarness) -> None:
        export(harness, 'brief', Selection(include=('e2', 'e3'), blocking=('e3',)))

        assert harness.read_markdown('brief') != PREVIOUS
