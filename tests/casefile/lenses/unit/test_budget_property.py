"""export: whatever the entries say, the output fits its budget or nothing is written."""

from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.errors import LensOverBudgetError
from red_thread_casefile.lenses import count_lines

from tests.casefile.ledger.builders import create_entry
from tests.casefile.lenses.builders import create_press_harness, export
from tests.casefile.lenses.cases import lens_shapes

if TYPE_CHECKING:
    from red_thread_casefile.services import Exported

    from tests.casefile.lenses.builders import PressHarness
    from tests.casefile.lenses.cases import LensShape

type Outcome = Exported | LensOverBudgetError


def create_text_lists(count: int) -> st.SearchStrategy[list[str]]:
    return st.lists(st.text(max_size=60), min_size=count, max_size=count)


class TestBudgetProperty:
    shapes = st.sampled_from(lens_shapes())
    texts = st.integers(min_value=0, max_value=260).flatmap(create_text_lists)

    def attempt(self, harness: PressHarness, shape: LensShape) -> Outcome:
        try:
            return export(harness, shape.name)
        except LensOverBudgetError as error:
            return error

    def stock(self, shape: LensShape, texts: list[str]) -> PressHarness:
        harness = create_press_harness()
        entries = (
            create_entry(seq=seq, kind=shape.fill_kind, text=text)
            for seq, text in enumerate(texts, 1)
        )
        harness.seed(*entries)
        return harness

    @given(shape=shapes, texts=texts)
    def test_the_output_is_within_budget_or_refused_with_nothing_written(
        self, shape: LensShape, texts: list[str]
    ) -> None:
        harness = self.stock(shape, texts)

        outcome = self.attempt(harness, shape)

        if isinstance(outcome, LensOverBudgetError):
            assert outcome.lines > shape.budget
            assert harness.snapshot() == {}
            return

        written = harness.read_markdown(shape.name)
        assert outcome.lines <= shape.budget
        assert count_lines(written) == outcome.lines
