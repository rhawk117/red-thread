"""export: the line budget of each lens and the lines it counts."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.errors import LensOverBudgetError
from red_thread_casefile.lenses import count_lines

from tests.casefile.lenses.builders import create_numbered_findings, create_press_harness, export
from tests.casefile.lenses.cases import lens_shape_params

if TYPE_CHECKING:
    from tests.casefile.lenses.builders import PressHarness
    from tests.casefile.lenses.cases import LensShape

PREVIOUS = 'a brief written by an earlier export\n'
SECTION_HEADING_LINES = 1


def measure_empty_output(shape: LensShape) -> int:
    return export(create_press_harness(), shape.name).lines


def lens_shape_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('shape', lens_shape_params())


class TestBudgetBoundary:
    @pytest.fixture
    def harness(self, press_harness: PressHarness) -> PressHarness:
        return press_harness

    def fill_to(self, harness: PressHarness, shape: LensShape, lines: int) -> None:
        count = lines - measure_empty_output(shape) - SECTION_HEADING_LINES
        harness.seed(*create_numbered_findings(shape.fill_kind, count))

    @lens_shape_cases()
    def test_output_exactly_at_the_budget_is_written(
        self, harness: PressHarness, shape: LensShape
    ) -> None:
        self.fill_to(harness, shape, shape.budget)

        exported = export(harness, shape.name)

        text = harness.read_markdown(shape.name)
        assert (exported.lines, exported.budget) == (shape.budget, shape.budget)
        assert count_lines(text) == shape.budget
        assert len(text.splitlines()) > shape.budget

    @lens_shape_cases()
    def test_output_one_line_over_the_budget_raises_with_the_figures(
        self, harness: PressHarness, shape: LensShape
    ) -> None:
        self.fill_to(harness, shape, shape.budget + 1)

        with pytest.raises(LensOverBudgetError) as raised:
            export(harness, shape.name)

        error = raised.value
        assert (error.lens, error.lines, error.budget) == (
            shape.name,
            shape.budget + 1,
            shape.budget,
        )

    @lens_shape_cases()
    def test_nothing_is_written_or_changed_when_over_budget(
        self, harness: PressHarness, shape: LensShape
    ) -> None:
        self.fill_to(harness, shape, shape.budget + 1)
        harness.pages.write(f'out/{shape.name}.md', PREVIOUS)
        before = harness.snapshot()

        with pytest.raises(LensOverBudgetError):
            export(harness, shape.name, html=True)

        assert harness.snapshot() == before

    def test_the_same_ledger_fits_the_report_budget_but_not_the_brief_budget(
        self, harness: PressHarness
    ) -> None:
        harness.seed(*create_numbered_findings('known', 50))

        report = export(harness, 'report')

        assert report.budget == 200
        with pytest.raises(LensOverBudgetError):
            export(harness, 'brief')


class TestCountLines:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            pytest.param('', 0, id='empty'),
            pytest.param('\n\n\n', 0, id='only-newlines'),
            pytest.param('   \n\t\n', 0, id='only-whitespace'),
            pytest.param('one', 1, id='one-line-without-newline'),
            pytest.param('one\ntwo\n', 2, id='two-lines'),
            pytest.param('one\n\n\ntwo\n', 2, id='blank-lines-between-do-not-count'),
            pytest.param('one\n   \ntwo', 2, id='whitespace-line-does-not-count'),
            pytest.param('  indented  \n', 1, id='indented-line-counts'),
        ],
    )
    def test_only_lines_that_carry_text_count(self, text: str, expected: int) -> None:
        assert count_lines(text) == expected
