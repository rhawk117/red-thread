"""The case map: a subgraph per thread, a node per entry, links in a thread, retirement edges."""

import string
from itertools import pairwise
from typing import TYPE_CHECKING

from hypothesis import example, given
from hypothesis import strategies as st
from red_thread_casefile.charts import MAIN_LEDGER, create_case_map, label_node
from red_thread_casefile.domain import ENTRY_KINDS, Ledger, order_thread

from tests.casefile.charts.builders import DANGLING_REF, EntrySpec, create_threaded_ledger
from tests.casefile.charts.reading import LABEL_CHARACTERS, read_map
from tests.casefile.ledger.builders import create_entry

if TYPE_CHECKING:
    from red_thread_casefile.domain import Entry, EntryKind

SAFE_CHARACTERS = string.ascii_letters + string.digits + ".,:/()+='-_"
HOSTILE = '"] --> x["y\n  end\n  subgraph z["w'


def thread_title(thread: str | None) -> str:
    return thread or MAIN_LEDGER


def list_names(ledger: Ledger) -> dict[str, str]:
    return {entry.ref: f'n{index}' for index, entry in enumerate(ledger.entries)}


def list_retired(ledger: Ledger) -> set[str]:
    refs = {entry.ref for entry in ledger.entries}
    return {ref for entry in ledger.entries for ref in entry.supersedes if ref in refs}


def list_threads(ledger: Ledger) -> list[str | None]:
    found = {entry.thread for entry in ledger.entries}
    main = [None] * (None in found)
    return [*main, *sorted((thread for thread in found if thread is not None), key=order_thread)]


class TestCaseMapProperties:
    specs = st.builds(
        EntrySpec,
        thread=st.sampled_from((None, 'T1', 'T2', 'T3', 'T10', 'T11')),
        kind=st.sampled_from(ENTRY_KINDS),
        text=st.text(max_size=60),
        retires=st.builds(tuple, st.lists(st.integers(min_value=0, max_value=20), max_size=3)),
        dangling=st.booleans(),
    )
    ledgers = st.lists(specs, max_size=14).map(create_threaded_ledger)

    @given(ledger=ledgers)
    def test_each_thread_with_entries_is_one_subgraph_main_first_then_in_numeric_order(
        self, ledger: Ledger
    ) -> None:
        drawn = read_map(create_case_map(ledger).render())

        assert list(drawn.titles) == [thread_title(thread) for thread in list_threads(ledger)]
        assert len(set(drawn.subgraph_ids)) == len(drawn.subgraph_ids)

    @given(ledger=ledgers)
    def test_each_entry_is_one_node_named_by_its_index_inside_its_threads_subgraph(
        self, ledger: Ledger
    ) -> None:
        drawn = read_map(create_case_map(ledger).render())

        names = list_names(ledger)
        nodes = {node.name: node for node in drawn.nodes}
        assert len(drawn.nodes) == len(ledger.entries)
        assert set(nodes) == set(names.values())
        for entry in ledger.entries:
            node = nodes[names[entry.ref]]
            assert node.label.startswith(f'{entry.ref} {entry.kind}: ')
            assert node.thread_title == thread_title(entry.thread)

    @given(ledger=ledgers)
    def test_a_node_takes_the_retired_class_exactly_when_a_later_entry_supersedes_it(
        self, ledger: Ledger
    ) -> None:
        drawn = read_map(create_case_map(ledger).render())

        names = list_names(ledger)
        retired = list_retired(ledger)
        styles = {node.name: node.style for node in drawn.nodes}
        for entry in ledger.entries:
            expected = 'k_retired' if entry.ref in retired else f'k_{entry.kind}'
            assert styles[names[entry.ref]] == expected

    @given(ledger=ledgers)
    def test_consecutive_entries_of_a_thread_are_linked_and_nothing_else_is(
        self, ledger: Ledger
    ) -> None:
        drawn = read_map(create_case_map(ledger).render())

        names = list_names(ledger)
        expected = []
        for thread in list_threads(ledger):
            members = [names[e.ref] for e in ledger.entries if e.thread == thread]
            expected.extend(pairwise(members))
        assert sorted(drawn.links) == sorted(expected)

    @given(ledger=ledgers)
    def test_each_supersedes_ref_that_exists_is_one_retirement_edge_from_the_superseder(
        self, ledger: Ledger
    ) -> None:
        drawn = read_map(create_case_map(ledger).render())

        names = list_names(ledger)
        expected = [
            (names[entry.ref], names[ref])
            for entry in ledger.entries
            for ref in entry.supersedes
            if ref in names
        ]
        assert sorted(drawn.retirements) == sorted(expected)
        assert all(DANGLING_REF not in line for line in create_case_map(ledger).render())

    @given(ledger=ledgers)
    def test_every_line_is_a_subgraph_a_node_a_link_a_retirement_or_an_end(
        self, ledger: Ledger
    ) -> None:
        lines = create_case_map(ledger).render()

        assert read_map(lines).strays == ()

    @given(ledger=ledgers)
    @example(ledger=create_threaded_ledger([EntrySpec(thread=None, kind='open', text=HOSTILE)]))
    def test_no_entry_text_adds_a_line_or_a_character_the_label_may_not_hold(
        self, ledger: Ledger
    ) -> None:
        lines = create_case_map(ledger).render()

        drawn = read_map(lines)
        assert drawn.strays == ()
        assert all(LABEL_CHARACTERS.fullmatch(node.label) for node in drawn.nodes)
        assert len(drawn.nodes) == len(ledger.entries)
        assert len(lines) == len(drawn.nodes) + len(drawn.titles) * 2 + len(drawn.links) + len(
            drawn.retirements
        )

    def test_an_empty_ledger_draws_nothing(self) -> None:
        assert create_case_map(Ledger()).render() == ()


class TestLabelNode:
    safe_words = st.text(alphabet=SAFE_CHARACTERS, min_size=1, max_size=6)
    safe_texts = st.lists(safe_words, min_size=1, max_size=3).map(' '.join)

    def create(self, text: str, *, thread: str | None = None, kind: EntryKind = 'known') -> Entry:
        return create_entry(seq=3, thread=thread, kind=kind, text=text)

    @given(text=safe_texts, kind=st.sampled_from(ENTRY_KINDS), thread=st.sampled_from((None, 'T2')))
    def test_a_short_text_of_allowed_characters_is_kept_whole_after_the_ref_and_kind(
        self, text: str, kind: EntryKind, thread: str | None
    ) -> None:
        entry = self.create(text, thread=thread, kind=kind)

        assert label_node(entry) == f'{entry.ref} {kind}: {text}'

    @given(text=st.text(max_size=200))
    def test_a_label_never_holds_a_character_outside_the_allowed_set(self, text: str) -> None:
        label = label_node(self.create(text))

        assert LABEL_CHARACTERS.fullmatch(label)
        assert label.startswith('e3 known: ')

    def test_a_long_text_is_shortened(self) -> None:
        text = ' '.join(['stalls'] * 60)

        label = label_node(self.create(text))

        assert len(label) < len(text) // 2

    def test_markup_and_quotes_in_the_text_leave_no_quote_bracket_or_angle(self) -> None:
        label = label_node(self.create('a "quoted" [part] <b>x</b> --> y'))

        assert not set('"[]<>') & set(label)
        assert 'quoted' in label
