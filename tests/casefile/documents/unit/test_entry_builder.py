"""The entry builder: one ledger entry becomes one typed entry node, whoever composes the page."""

from typing import get_args

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.documents import Citation, EntryBuilder
from red_thread_casefile.domain import EntryKind
from red_thread_casefile.packaged import load_wording
from red_thread_casefile.policy import Finding
from red_thread_casefile.views import Annotator
from red_thread_core.documents import parse_line
from red_thread_core.util import squeeze

from tests.casefile.ledger.builders import create_entry

BOARD_HEAD = 'a' * 40
OLD_HEAD = 'b' * 40


class TestCarriedFields:
    builder = EntryBuilder(annotator=Annotator(head=BOARD_HEAD))
    kinds = st.sampled_from(get_args(EntryKind.__value__))
    threads = st.sampled_from((None, 'T1', 'T10'))

    @given(kind=kinds, thread=threads, seq=st.integers(min_value=1, max_value=99))
    def test_ref_kind_thread_round_and_day_are_carried_over(
        self, kind: EntryKind, thread: str | None, seq: int
    ) -> None:
        entry = create_entry(seq=seq, kind=kind, thread=thread, head=BOARD_HEAD)

        node = self.builder.build(entry)

        carried = (node.ref, node.kind, node.thread, node.round, node.at)
        assert carried == (entry.ref, entry.kind, entry.thread, entry.round, entry.at)

    def test_the_claim_is_the_squeezed_text_split_into_code_spans(self) -> None:
        text = 'run `make check`\n   before   the push'
        entry = create_entry(text=text, head=BOARD_HEAD)

        assert self.builder.build(entry).claim == parse_line(squeeze(text))

    def test_a_known_entry_shows_no_verdict_and_others_show_theirs(self) -> None:
        known = create_entry(kind='known', verdict='VERIFIED', head=BOARD_HEAD)
        hypothesis = create_entry(kind='hypothesis', verdict='INFERRED', head=BOARD_HEAD)

        assert self.builder.build(known).verdict is None
        assert self.builder.build(hypothesis).verdict == 'INFERRED'

    def test_the_diagram_is_carried_over(self) -> None:
        entry = create_entry(diagram='flowchart TD\n  A --> B', head=BOARD_HEAD)

        assert self.builder.build(entry).diagram == entry.diagram


class TestCitation:
    cite = 'src/queue.py:3'
    finding = Finding(ref='e1', cite=cite, state='moved', moved_to=9)
    builder = EntryBuilder(annotator=Annotator(head=BOARD_HEAD, findings=(finding,)))

    def test_an_entry_without_a_cite_has_no_citation(self) -> None:
        assert self.builder.build(create_entry(head=BOARD_HEAD)).citation is None

    def test_a_quote_without_a_cite_gives_no_citation(self) -> None:
        assert self.builder.build(create_entry(quote='sleep(5)', head=BOARD_HEAD)).citation is None

    def test_a_citation_carries_its_quote_and_its_finding(self) -> None:
        entry = create_entry(seq=1, cite=self.cite, quote='sleep(5)', head=BOARD_HEAD)

        expected = Citation(target=self.cite, quote='sleep(5)', finding=self.finding)
        assert self.builder.build(entry).citation == expected


class TestLead:
    builder = EntryBuilder(annotator=Annotator(head=BOARD_HEAD))

    def test_an_entry_recorded_at_the_board_commit_is_not_a_lead(self) -> None:
        assert self.builder.build(create_entry(head=BOARD_HEAD)).lead is None

    def test_an_entry_from_another_commit_names_that_commit_shortened(self) -> None:
        node = self.builder.build(create_entry(head=OLD_HEAD))

        assert node.flags == ('lead, recorded at bbbbbbb',)

    def test_an_entry_with_no_commit_is_a_lead_with_no_commit(self) -> None:
        assert self.builder.build(create_entry(head=None)).lead == 'no commit'


class TestNotes:
    builder = EntryBuilder(annotator=Annotator(head=BOARD_HEAD))

    def test_the_notes_given_are_the_notes_kept_in_order(self) -> None:
        notes = (
            load_wording().write_note('urgency', 'blocking'),
            load_wording().write_note('source', 'scout'),
        )

        assert self.builder.build(create_entry(head=BOARD_HEAD), notes).notes == notes

    def test_caveats_are_rests_on_then_refuted_by(self) -> None:
        entry = create_entry(rests_on='a 4.x docs page', refute='a passing run')

        assert load_wording().list_caveat_notes(entry) == (
            load_wording().write_note('rests_on', 'a 4.x docs page'),
            load_wording().write_note('refuted_by', 'a passing run'),
        )

    def test_an_entry_without_caveats_has_none(self) -> None:
        assert load_wording().list_caveat_notes(create_entry()) == ()
