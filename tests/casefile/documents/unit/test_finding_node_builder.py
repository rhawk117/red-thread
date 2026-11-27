"""FindingNodeBuilder: one ledger finding becomes one typed finding node for any page."""

from typing import get_args

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.documents import CitationNode, FindingNodeBuilder
from red_thread_casefile.domain import FindingKind
from red_thread_casefile.packaged import load_wording
from red_thread_casefile.policy import CitationCheck
from red_thread_casefile.views import Annotator
from red_thread_core.documents import parse_line
from red_thread_core.util import squeeze

from tests.casefile.ledger.builders import create_finding

BOARD_HEAD = 'a' * 40
OLD_HEAD = 'b' * 40


class TestCarriedFields:
    builder = FindingNodeBuilder(annotator=Annotator(head=BOARD_HEAD))
    kinds = st.sampled_from(get_args(FindingKind.__value__))
    threads = st.sampled_from((None, 'T1', 'T10'))

    @given(kind=kinds, thread=threads, finding_number=st.integers(min_value=1, max_value=99))
    def test_finding_id_kind_thread_round_and_day_are_carried_over(
        self, kind: FindingKind, thread: str | None, finding_number: int
    ) -> None:
        finding = create_finding(
            finding_number=finding_number, kind=kind, thread=thread, head=BOARD_HEAD
        )

        node = self.builder.build(finding)

        carried = (node.finding_id, node.kind, node.thread, node.round, node.at)
        assert carried == (
            finding.finding_id,
            finding.kind,
            finding.thread,
            finding.round,
            finding.at,
        )

    def test_the_claim_is_the_squeezed_text_split_into_code_spans(self) -> None:
        text = 'run `make check`\n   before   the push'
        finding = create_finding(text=text, head=BOARD_HEAD)

        assert self.builder.build(finding).claim == parse_line(squeeze(text))

    def test_a_known_finding_shows_no_verdict_and_others_show_theirs(self) -> None:
        known = create_finding(kind='known', verdict='VERIFIED', head=BOARD_HEAD)
        hypothesis = create_finding(kind='hypothesis', verdict='INFERRED', head=BOARD_HEAD)

        assert self.builder.build(known).verdict is None
        assert self.builder.build(hypothesis).verdict == 'INFERRED'

    def test_the_diagram_is_carried_over(self) -> None:
        finding = create_finding(diagram='flowchart TD\n  A --> B', head=BOARD_HEAD)

        assert self.builder.build(finding).diagram == finding.diagram


class TestCitation:
    citation = 'src/queue.py:3'
    citation_check = CitationCheck(finding_id='e1', citation=citation, state='moved', moved_to=9)
    builder = FindingNodeBuilder(
        annotator=Annotator(head=BOARD_HEAD, citation_checks=(citation_check,))
    )

    def test_an_finding_without_a_citation_has_no_citation(self) -> None:
        assert self.builder.build(create_finding(head=BOARD_HEAD)).citation_node is None

    def test_a_quote_without_a_citation_gives_no_citation(self) -> None:
        assert (
            self.builder.build(create_finding(quote='sleep(5)', head=BOARD_HEAD)).citation_node
            is None
        )

    def test_a_citation_carries_its_quote_and_its_citation_check(self) -> None:
        finding = create_finding(
            finding_number=1, citation=self.citation, quote='sleep(5)', head=BOARD_HEAD
        )

        expected = CitationNode(
            target=self.citation, quote='sleep(5)', citation_check=self.citation_check
        )
        assert self.builder.build(finding).citation_node == expected


class TestLead:
    builder = FindingNodeBuilder(annotator=Annotator(head=BOARD_HEAD))

    def test_an_finding_recorded_at_the_board_commit_is_not_a_lead(self) -> None:
        assert self.builder.build(create_finding(head=BOARD_HEAD)).lead is None

    def test_an_finding_from_another_commit_names_that_commit_shortened(self) -> None:
        node = self.builder.build(create_finding(head=OLD_HEAD))

        assert node.flags == ('lead, recorded at bbbbbbb',)

    def test_an_finding_with_no_commit_is_a_lead_with_no_commit(self) -> None:
        assert self.builder.build(create_finding(head=None)).lead == 'no commit'


class TestNotes:
    builder = FindingNodeBuilder(annotator=Annotator(head=BOARD_HEAD))

    def test_the_notes_given_are_the_notes_kept_in_order(self) -> None:
        notes = (
            load_wording().write_note('urgency', 'blocking'),
            load_wording().write_note('source', 'scout'),
        )

        assert self.builder.build(create_finding(head=BOARD_HEAD), notes).notes == notes

    def test_caveats_are_rests_on_then_refuted_by(self) -> None:
        finding = create_finding(rests_on='a 4.x docs page', refuted_if='a passing run')

        assert load_wording().list_caveat_notes(finding) == (
            load_wording().write_note('rests_on', 'a 4.x docs page'),
            load_wording().write_note('refuted_by', 'a passing run'),
        )

    def test_an_finding_without_caveats_has_none(self) -> None:
        assert load_wording().list_caveat_notes(create_finding()) == ()
