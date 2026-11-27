"""CaseFile.check: one finding per live cited finding, with the state its source file gives."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st

from tests.casefile.ledger.builders import create_finding
from tests.casefile.services.fakes import create_service_harness

if TYPE_CHECKING:
    from red_thread_casefile.domain import CaseFinding
    from red_thread_casefile.policy import CitationState

    from tests.casefile.services.fakes import ServiceHarness

SOURCE = 'src/a.py'
LINES = ('alpha', 'beta')
URL = 'https://example.invalid/docs'
CITATIONS = (None, URL, f'{SOURCE}:1')
THREADS = (None, 'T1', 'T2')


@dataclass(slots=True, kw_only=True, frozen=True)
class SourceChange:
    name: str
    lines: tuple[str, ...] | None
    state: CitationState
    moved_to: int | None = None


SOURCE_CHANGES = (
    SourceChange(name='untouched', lines=LINES, state='ok'),
    SourceChange(name='edited', lines=('gamma', 'delta'), state='changed'),
    SourceChange(name='shifted', lines=('inserted', *LINES), state='moved', moved_to=2),
    SourceChange(name='deleted', lines=None, state='missing'),
)


def create_lead(thread: str | None, citation: str | None) -> CaseFinding:
    quote = LINES[0] if citation == f'{SOURCE}:1' else None
    return create_finding(thread=thread, text='a lead', citation=citation, quote=quote)


def create_retirement(finding_id: str) -> CaseFinding:
    thread = finding_id.partition('.')[0] if '.' in finding_id else None
    return create_finding(thread=thread, text='a retirement', supersedes=(finding_id,))


def write_next(harness: ServiceHarness, finding: CaseFinding) -> None:
    harness.seed(finding.replace_with(finding_number=len(harness.scribe.files[finding.thread]) + 1))


class TestCheckProperties:
    cited_adds = st.lists(
        st.tuples(st.sampled_from(THREADS), st.sampled_from(CITATIONS)), max_size=8
    )
    changes = st.sampled_from(SOURCE_CHANGES)

    def stock(self, adds: list[tuple[str | None, str | None]]) -> ServiceHarness:
        harness = create_service_harness({SOURCE: LINES})
        for thread, citation in adds:
            write_next(harness, create_lead(thread, citation))
        return harness

    def retire(self, harness: ServiceHarness, finding_ids: list[str]) -> None:
        for finding_id in finding_ids:
            write_next(harness, create_retirement(finding_id))

    @given(adds=cited_adds, change=changes, data=st.data())
    def test_one_citation_check_per_live_cited_finding_in_the_state_its_source_gives(
        self, adds: list[tuple[str | None, str | None]], change: SourceChange, data: st.DataObject
    ) -> None:
        harness = self.stock(adds)
        finding_ids = [finding.finding_id for finding in harness.read_findings()]
        retired = (
            data.draw(st.lists(st.sampled_from(finding_ids), unique=True)) if finding_ids else []
        )
        self.retire(harness, retired)
        harness.tree.remove(SOURCE)
        if change.lines is not None:
            harness.tree.write(SOURCE, change.lines)

        citation_checks = harness.case_file.check().citation_checks

        live_cited = [e for e in harness.case_file.load().ledger.live if e.citation is not None]
        assert [citation_check.finding_id for citation_check in citation_checks] == [
            finding.finding_id for finding in live_cited
        ]
        for citation_check in citation_checks:
            is_path = citation_check.citation == f'{SOURCE}:1'
            assert citation_check.state == (change.state if is_path else 'unchecked')
            assert citation_check.moved_to == (change.moved_to if is_path else None)
