"""The budget policy: estimates, rung selection, cutting and the minimum."""

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_navigate.budget import (
    MIN_BUDGET,
    BudgetBelowMinimumError,
    BudgetError,
    NoRungsError,
    cut_to_budget,
    estimate_tokens,
    fit_notes,
    fit_to_budget,
)


def is_one_line(text: str) -> bool:
    return '\n' not in text


lines_strategy = st.lists(st.text(max_size=2000).filter(is_one_line), max_size=40)
rungs_strategy = st.lists(lines_strategy.map(tuple), min_size=1, max_size=3)


class TestEstimateTokens:
    def test_dense_code_counts_at_most_three_and_a_half_characters_per_token(self) -> None:
        assert estimate_tokens('x' * 35) >= 10

    def test_empty_text_is_free(self) -> None:
        assert estimate_tokens('') == 0


class TestFitToBudget:
    @given(rungs=rungs_strategy, budget=st.integers(min_value=MIN_BUDGET, max_value=5000))
    def test_fitted_output_never_exceeds_the_budget(
        self, rungs: list[tuple[str, ...]], budget: int
    ) -> None:
        fitted = fit_to_budget(rungs, budget=budget)

        assert estimate_tokens(fitted.text) <= budget

    def test_first_rung_that_fits_is_returned_whole(self) -> None:
        rungs = [tuple('x' * 40 for _ in range(20)), ('summary line',), ('3 files',)]

        fitted = fit_to_budget(rungs, budget=100)

        assert (fitted.text, fitted.rung, fitted.cut) == ('summary line', 1, False)

    def test_last_rung_is_cut_at_a_line_boundary_with_a_footer(self) -> None:
        lines = tuple(f'line number {i:03d}' for i in range(100))

        fitted = fit_to_budget([lines], budget=60)

        assert fitted.cut
        assert 0 < fitted.kept < 100
        assert fitted.text.splitlines() == [
            *lines[: fitted.kept],
            f'showing {fitted.kept} of 100, raise --budget',
        ]

    def test_budget_below_the_minimum_is_refused_naming_it(self) -> None:
        with pytest.raises(BudgetBelowMinimumError, match=str(MIN_BUDGET)) as caught:
            fit_to_budget([('a',)], budget=MIN_BUDGET - 1)

        assert isinstance(caught.value, BudgetError)

    def test_no_rungs_is_refused(self) -> None:
        with pytest.raises(NoRungsError):
            fit_to_budget([], budget=MIN_BUDGET)

    def test_first_line_longer_than_the_budget_leaves_only_the_footer(self) -> None:
        rung = ('z' * 3000, 'short')

        fitted = fit_to_budget([rung], budget=MIN_BUDGET)

        assert estimate_tokens(fitted.text) <= MIN_BUDGET
        assert fitted.text == 'showing 0 of 2, raise --budget'
        assert fitted.kept == 0

    def test_minimum_budget_holds_the_footer_for_a_huge_rung(self) -> None:
        fitted = fit_to_budget([tuple('y' * 50 for _ in range(10_000))], budget=MIN_BUDGET)

        assert estimate_tokens(fitted.text) <= MIN_BUDGET
        assert fitted.text.endswith('of 10000, raise --budget')


class TestFitNotes:
    def test_notes_inside_their_share_are_kept_whole(self) -> None:
        assert fit_notes(('a', 'b'), budget=MIN_BUDGET) == ('a', 'b')

    def test_a_note_longer_than_the_share_leaves_only_the_count(self) -> None:
        assert fit_notes(('n' * 500,), budget=MIN_BUDGET) == ('and 1 more notes',)


class TestPrintedFit:
    def test_fitted_text_with_its_newline_is_not_cut_again(self) -> None:
        fitted = fit_to_budget([tuple('x' * 20 for _ in range(30))], budget=MIN_BUDGET)

        assert cut_to_budget(fitted.text, MIN_BUDGET) == fitted.text
