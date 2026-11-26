"""CaseFile.check: one finding per live cited entry, with the state its source file gives."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st
from msgspec.structs import replace

from tests.casefile.ledger.builders import create_entry
from tests.casefile.services.fakes import create_service_harness

if TYPE_CHECKING:
    from red_thread_casefile.domain import Entry
    from red_thread_casefile.policy import CiteState

    from tests.casefile.services.fakes import ServiceHarness

SOURCE = 'src/a.py'
LINES = ('alpha', 'beta')
URL = 'https://example.invalid/docs'
CITES = (None, URL, f'{SOURCE}:1')
THREADS = (None, 'T1', 'T2')


@dataclass(slots=True, kw_only=True, frozen=True)
class SourceChange:
    name: str
    lines: tuple[str, ...] | None
    state: CiteState
    moved_to: int | None = None


SOURCE_CHANGES = (
    SourceChange(name='untouched', lines=LINES, state='ok'),
    SourceChange(name='edited', lines=('gamma', 'delta'), state='changed'),
    SourceChange(name='shifted', lines=('inserted', *LINES), state='moved', moved_to=2),
    SourceChange(name='deleted', lines=None, state='missing'),
)


def create_lead(thread: str | None, cite: str | None) -> Entry:
    quote = LINES[0] if cite == f'{SOURCE}:1' else None
    return create_entry(thread=thread, text='a lead', cite=cite, quote=quote)


def create_retirement(ref: str) -> Entry:
    thread = ref.partition('.')[0] if '.' in ref else None
    return create_entry(thread=thread, text='a retirement', supersedes=(ref,))


def write_next(harness: ServiceHarness, entry: Entry) -> None:
    harness.seed(replace(entry, seq=len(harness.scribe.files[entry.thread]) + 1))


class TestCheckProperties:
    cited_adds = st.lists(st.tuples(st.sampled_from(THREADS), st.sampled_from(CITES)), max_size=8)
    changes = st.sampled_from(SOURCE_CHANGES)

    def stock(self, adds: list[tuple[str | None, str | None]]) -> ServiceHarness:
        harness = create_service_harness({SOURCE: LINES})
        for thread, cite in adds:
            write_next(harness, create_lead(thread, cite))
        return harness

    def retire(self, harness: ServiceHarness, refs: list[str]) -> None:
        for ref in refs:
            write_next(harness, create_retirement(ref))

    @given(adds=cited_adds, change=changes, data=st.data())
    def test_one_finding_per_live_cited_entry_in_the_state_its_source_gives(
        self, adds: list[tuple[str | None, str | None]], change: SourceChange, data: st.DataObject
    ) -> None:
        harness = self.stock(adds)
        refs = [entry.ref for entry in harness.read_entries()]
        retired = data.draw(st.lists(st.sampled_from(refs), unique=True)) if refs else []
        self.retire(harness, retired)
        harness.tree.remove(SOURCE)
        if change.lines is not None:
            harness.tree.write(SOURCE, change.lines)

        findings = harness.case_file.check().findings

        live_cited = [e for e in harness.case_file.load().ledger.live if e.cite is not None]
        assert [finding.ref for finding in findings] == [entry.ref for entry in live_cited]
        for finding in findings:
            is_path = finding.cite == f'{SOURCE}:1'
            assert finding.state == (change.state if is_path else 'unchecked')
            assert finding.moved_to == (change.moved_to if is_path else None)
