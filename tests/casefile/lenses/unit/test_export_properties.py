"""Press.export: within budget or refused with nothing written, and only live refs are named."""

import re
import string
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.errors import LensOverBudgetError, UnknownSelectionRefError
from red_thread_casefile.lenses import LENS_NAMES, Selection, count_lines
from red_thread_casefile.packaged import load_lens_book
from red_thread_casefile.services import ExportRequest

from tests.casefile.entries.strategies import entry_kinds
from tests.casefile.ledger.builders import create_entry
from tests.casefile.services.fakes import create_service_harness

if TYPE_CHECKING:
    from red_thread_casefile.domain import EntryKind
    from red_thread_casefile.lenses import LensName
    from red_thread_casefile.services import Exported

    from tests.casefile.services.fakes import ServiceHarness

type Outcome = Exported | LensOverBudgetError
type Spec = tuple[EntryKind, str, bool]

NAMED_REF = re.compile(r' \[((?:T\d+\.)?e\d+)\]$')


def retiring(index: int, retires: bool) -> tuple[str, ...]:
    if retires and index > 1:
        return (f'e{index - 1}',)
    return ()


def list_named_refs(markdown: str) -> list[str]:
    items = (line for line in markdown.split('\n') if line.startswith('- '))
    found = (NAMED_REF.search(line) for line in items)
    return [match[1] for match in found if match]


class TestExportProperties:
    lenses = st.sampled_from(LENS_NAMES)
    letters = st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=12)
    specs = st.lists(st.tuples(entry_kinds, letters, st.booleans()), max_size=70)

    def stock(self, specs: list[Spec]) -> ServiceHarness:
        harness = create_service_harness()
        entries = (
            create_entry(seq=index, kind=kind, text=text, supersedes=retiring(index, retires))
            for index, (kind, text, retires) in enumerate(specs, 1)
        )
        harness.seed(*entries)
        return harness

    def attempt(self, harness: ServiceHarness, request: ExportRequest) -> Outcome:
        try:
            return harness.press.export(request)
        except LensOverBudgetError as error:
            return error

    @given(specs=specs, lens=lenses, html=st.booleans())
    def test_the_output_fits_its_budget_or_nothing_is_written(
        self, specs: list[Spec], lens: LensName, html: bool
    ) -> None:
        harness = self.stock(specs)
        request = ExportRequest(lens=lens, html=html)

        outcome = self.attempt(harness, request)

        if isinstance(outcome, LensOverBudgetError):
            assert outcome.lines > load_lens_book().get(lens).budget
            assert harness.pages.files == {}
            return

        written = harness.pages.read(f'out/{lens}.md') or ''
        assert outcome.lines <= load_lens_book().get(lens).budget
        assert count_lines(written) == outcome.lines
        assert (harness.pages.read(f'out/{lens}.html') is not None) == html

    @given(specs=specs, lens=lenses)
    def test_every_ref_the_output_names_is_a_live_entry(
        self, specs: list[Spec], lens: LensName
    ) -> None:
        harness = self.stock(specs)

        outcome = self.attempt(harness, ExportRequest(lens=lens))

        if isinstance(outcome, LensOverBudgetError):
            return

        live = {entry.ref for entry in harness.case_file.load().ledger.live}
        named = list_named_refs(harness.pages.read(f'out/{lens}.md') or '')
        assert set(named) <= live
        assert len(named) == len(set(named))

    @given(specs=specs, data=st.data())
    def test_an_include_list_limits_the_refs_to_its_entries_and_the_decisions(
        self, specs: list[Spec], data: st.DataObject
    ) -> None:
        harness = self.stock(specs)
        ledger = harness.case_file.load().ledger
        live = [entry.ref for entry in ledger.live]
        include = data.draw(st.lists(st.sampled_from(live), unique=True)) if live else []
        request = ExportRequest(lens='report', selection=Selection(include=tuple(include)))

        harness.press.export(request)

        decisions = {entry.ref for entry in ledger.live if entry.kind == 'decision'}
        named = list_named_refs(harness.pages.read('out/report.md') or '')
        assert set(named) <= {*include, *decisions}
        assert set(include) <= set(named)

    @given(specs=specs, lens=lenses, missing=st.sampled_from(('e999', 'T9.e1')))
    def test_a_selection_naming_an_entry_that_is_not_live_is_refused_and_writes_nothing(
        self, specs: list[Spec], lens: LensName, missing: str
    ) -> None:
        harness = self.stock(specs)
        request = ExportRequest(lens=lens, selection=Selection(include=(missing,)))

        with pytest.raises(UnknownSelectionRefError) as raised:
            harness.press.export(request)

        assert raised.value.ref == missing
        assert harness.pages.files == {}
