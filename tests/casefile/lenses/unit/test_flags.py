"""export: what an entry is flagged with in the Markdown output."""

from typing import TYPE_CHECKING

import pytest

from tests.casefile.lenses.builders import seed_flag_scenario
from tests.casefile.lenses.cases import flag_params, flag_scenarios
from tests.casefile.lenses.reading import find_item, list_remarks

if TYPE_CHECKING:
    from tests.casefile.lenses.builders import PressHarness
    from tests.casefile.lenses.cases import FlagScenario


def flag_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('scenario', flag_params())


class TestFlagsInMarkdown:
    @flag_cases()
    def test_entry_carries_exactly_the_flags_its_situation_calls_for(
        self, press_harness: PressHarness, scenario: FlagScenario
    ) -> None:
        seed_flag_scenario(press_harness, scenario)

        text = press_harness.export_markdown('brief')

        assert list_remarks(find_item(text, 'e1')) == list(scenario.flags)

    def test_a_flag_is_written_in_every_lens_that_lists_the_entry(
        self, press_harness: PressHarness
    ) -> None:
        scenario = next(
            item for item in flag_scenarios() if item.name == 'recorded-at-another-commit'
        )
        seed_flag_scenario(press_harness, scenario)

        written = {
            lens: list_remarks(find_item(press_harness.export_markdown(lens), 'e1'))
            for lens in ('brief', 'issue', 'report')
        }

        assert written == {lens: list(scenario.flags) for lens in written}
