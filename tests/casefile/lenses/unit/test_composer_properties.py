"""Selection and Composer: what a selection admits and how it orders the entries it selects."""

from typing import TYPE_CHECKING

import msgspec
from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.domain import ENTRY_KINDS, Ledger
from red_thread_casefile.lenses import Composer, Edition, Selection, count_lines, get_lens

from tests.casefile.entries.strategies import POOLED_REFS, optional, pooled_entries, words
from tests.casefile.ledger.builders import create_entry
from tests.casefile.services.fakes import CASE

if TYPE_CHECKING:
    from red_thread_casefile.domain import Entry


def pick_refs(refs: tuple[str, ...]) -> st.SearchStrategy[tuple[str, ...]]:
    return st.builds(tuple, st.lists(st.sampled_from(refs), unique=True, max_size=len(refs)))


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
    pooled_refs = pick_refs(POOLED_REFS)
    selections = st.builds(Selection, include=optional(pooled_refs), blocking=optional(pooled_refs))
    open_selections = st.builds(Selection, include=st.none(), blocking=optional(pooled_refs))
    decisions = st.builds(msgspec.structs.replace, pooled_entries, kind=st.just('decision'))
    others = st.builds(
        msgspec.structs.replace,
        pooled_entries,
        kind=st.sampled_from([kind for kind in ENTRY_KINDS if kind != 'decision']),
    )

    @given(selection=selections, entry=decisions)
    def test_a_decision_is_always_admitted(self, selection: Selection, entry: Entry) -> None:
        assert selection.admits(entry)

    @given(selection=open_selections, entry=pooled_entries)
    def test_a_selection_without_an_include_list_admits_everything(
        self, selection: Selection, entry: Entry
    ) -> None:
        assert selection.admits(entry)

    @given(selection=selections, entry=others)
    def test_otherwise_only_an_included_or_blocking_entry_is_admitted(
        self, selection: Selection, entry: Entry
    ) -> None:
        named = entry.ref in (selection.include or ()) or entry.ref in (selection.blocking or ())

        assert selection.admits(entry) == (selection.include is None or named)


class TestComposerSelect:
    counts = st.integers(min_value=1, max_value=8)

    def create_composer(self, count: int, selection: Selection) -> tuple[Composer, list[str]]:
        entries = tuple(create_entry(seq=seq) for seq in range(1, count + 1))
        edition = Edition(case=CASE, ledger=Ledger(entries=entries))
        refs = [entry.ref for entry in entries]
        return Composer(lens=get_lens('brief'), selection=selection, edition=edition), refs

    @given(count=counts, data=st.data())
    def test_blocking_entries_come_first_and_the_rest_keep_the_include_order(
        self, count: int, data: st.DataObject
    ) -> None:
        refs = [f'e{seq}' for seq in range(1, count + 1)]
        include = data.draw(pick_refs(tuple(refs)))
        blocking = data.draw(pick_refs(tuple(refs)))
        composer, _ = self.create_composer(count, Selection(include=include, blocking=blocking))

        selected = [entry.ref for entry in composer.select('open')]

        urgent = [ref for ref in include if ref in blocking]
        urgent_outside = [ref for ref in refs if ref in blocking and ref not in include]
        calm = [ref for ref in include if ref not in blocking]
        assert selected == [*urgent, *urgent_outside, *calm]

    @given(count=counts, data=st.data())
    def test_without_an_include_list_every_entry_is_kept_and_blocking_ones_lead(
        self, count: int, data: st.DataObject
    ) -> None:
        refs = [f'e{seq}' for seq in range(1, count + 1)]
        blocking = data.draw(pick_refs(tuple(refs)))
        composer, _ = self.create_composer(count, Selection(blocking=blocking))

        selected = [entry.ref for entry in composer.select('open')]

        urgent = [ref for ref in refs if ref in blocking]
        assert selected == [*urgent, *[ref for ref in refs if ref not in blocking]]
