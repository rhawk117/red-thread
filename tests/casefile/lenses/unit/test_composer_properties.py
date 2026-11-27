"""Selection and Composer: what a selection admits and how it orders the findings it selects."""

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.domain import FINDING_KINDS, CaseFinding, CaseLedger
from red_thread_casefile.lenses import Composer, Edition, Selection, count_lines
from red_thread_casefile.packaged import load_lens_book, load_wording

from tests.casefile.findings.strategies import POOLED_REFS, optional, pooled_findings, words
from tests.casefile.ledger.builders import create_finding
from tests.casefile.services.fakes import CASE


def pick_finding_ids(finding_ids: tuple[str, ...]) -> st.SearchStrategy[tuple[str, ...]]:
    return st.builds(
        tuple, st.lists(st.sampled_from(finding_ids), unique=True, max_size=len(finding_ids))
    )


class TestCountLines:
    lines = st.lists(
        st.one_of(st.just(''), st.text(alphabet=' \t', max_size=3), words), max_size=20
    )
    separators = st.sampled_from(('\n', '\r\n'))

    @given(lines=lines, separator=separators)
    def test_it_counts_the_lines_that_carry_text(self, lines: list[str], separator: str) -> None:
        text = separator.join(lines)

        assert count_lines(text) == len([line for line in lines if line.strip()])


class TestSelectionAdmits:
    pooled_finding_ids = pick_finding_ids(POOLED_REFS)
    selections = st.builds(
        Selection, include=optional(pooled_finding_ids), blocking=optional(pooled_finding_ids)
    )
    open_selections = st.builds(Selection, include=st.none(), blocking=optional(pooled_finding_ids))
    decisions = st.builds(CaseFinding.replace_with, pooled_findings, kind=st.just('decision'))
    others = st.builds(
        CaseFinding.replace_with,
        pooled_findings,
        kind=st.sampled_from([kind for kind in FINDING_KINDS if kind != 'decision']),
    )

    @given(selection=selections, finding=decisions)
    def test_a_decision_is_always_admitted(
        self, selection: Selection, finding: CaseFinding
    ) -> None:
        assert selection.admits(finding)

    @given(selection=open_selections, finding=pooled_findings)
    def test_a_selection_without_an_include_list_admits_everything(
        self, selection: Selection, finding: CaseFinding
    ) -> None:
        assert selection.admits(finding)

    @given(selection=selections, finding=others)
    def test_otherwise_only_an_included_or_blocking_finding_is_admitted(
        self, selection: Selection, finding: CaseFinding
    ) -> None:
        named = finding.finding_id in (selection.include or ()) or finding.finding_id in (
            selection.blocking or ()
        )

        assert selection.admits(finding) == (selection.include is None or named)


class TestComposerSelect:
    counts = st.integers(min_value=1, max_value=8)

    def create_composer(self, count: int, selection: Selection) -> tuple[Composer, list[str]]:
        findings = tuple(
            create_finding(finding_number=finding_number) for finding_number in range(1, count + 1)
        )
        edition = Edition(case=CASE, ledger=CaseLedger(findings=findings))
        finding_ids = [finding.finding_id for finding in findings]
        return Composer(
            lens=load_lens_book().get('brief'),
            selection=selection,
            edition=edition,
            wording=load_wording(),
            reading=load_lens_book().reading,
        ), finding_ids

    @given(count=counts, data=st.data())
    def test_blocking_findings_come_first_and_the_rest_keep_the_include_order(
        self, count: int, data: st.DataObject
    ) -> None:
        finding_ids = [f'e{finding_number}' for finding_number in range(1, count + 1)]
        include = data.draw(pick_finding_ids(tuple(finding_ids)))
        blocking = data.draw(pick_finding_ids(tuple(finding_ids)))
        composer, _ = self.create_composer(count, Selection(include=include, blocking=blocking))

        selected = [finding.finding_id for finding in composer.select('open')]

        urgent = [finding_id for finding_id in include if finding_id in blocking]
        urgent_outside = [
            finding_id
            for finding_id in finding_ids
            if finding_id in blocking and finding_id not in include
        ]
        calm = [finding_id for finding_id in include if finding_id not in blocking]
        assert selected == [*urgent, *urgent_outside, *calm]

    @given(count=counts, data=st.data())
    def test_without_an_include_list_every_finding_is_kept_and_blocking_ones_lead(
        self, count: int, data: st.DataObject
    ) -> None:
        finding_ids = [f'e{finding_number}' for finding_number in range(1, count + 1)]
        blocking = data.draw(pick_finding_ids(tuple(finding_ids)))
        composer, _ = self.create_composer(count, Selection(blocking=blocking))

        selected = [finding.finding_id for finding in composer.select('open')]

        urgent = [finding_id for finding_id in finding_ids if finding_id in blocking]
        assert selected == [
            *urgent,
            *[finding_id for finding_id in finding_ids if finding_id not in blocking],
        ]
