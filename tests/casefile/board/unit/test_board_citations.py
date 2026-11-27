"""The shown board flags a citation the tree no longer supports, as the page does."""

from typing import TYPE_CHECKING

import pytest

from tests.casefile.lenses.builders import FLAGGED_TEXT, seed_flag_scenario
from tests.casefile.lenses.cases import flag_params

if TYPE_CHECKING:
    from tests.casefile.lenses.builders import PressHarness
    from tests.casefile.lenses.cases import FlagScenario


def flag_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('scenario', flag_params())


def find_claim_line(text: str) -> str:
    (line,) = [line for line in text.splitlines() if FLAGGED_TEXT in line]
    return line


class TestShownCitations:
    @flag_cases()
    def test_shown_board_carries_the_flags_of_a_cited_finding(
        self, press_harness: PressHarness, scenario: FlagScenario
    ) -> None:
        seed_flag_scenario(press_harness, scenario)

        line = find_claim_line(press_harness.case.casefile.show())

        assert [flag for flag in scenario.flags if flag not in line] == []
        assert ('citation_node' in line) == any('citation_node' in flag for flag in scenario.flags)
