"""The case map: a subgraph per thread, a node per finding, links in a thread, retirement edges."""

import string
from itertools import pairwise
from typing import TYPE_CHECKING

from hypothesis import example, given
from hypothesis import strategies as st
from red_thread_casefile.charts import MAIN_LEDGER, create_case_map, label_node
from red_thread_casefile.domain import FINDING_KINDS, CaseLedger, order_thread

from tests.casefile.charts.builders import DANGLING_REF, FindingSpec, create_threaded_ledger
from tests.casefile.charts.reading import LABEL_CHARACTERS, read_map
from tests.casefile.ledger.builders import create_finding

if TYPE_CHECKING:
    from red_thread_casefile.domain import CaseFinding, FindingKind

SAFE_CHARACTERS = string.ascii_letters + string.digits + ".,:/()+='-_"
HOSTILE = '"] --> x["y\n  end\n  subgraph z["w'


def thread_title(thread: str | None) -> str:
    return thread or MAIN_LEDGER


def list_names(ledger: CaseLedger) -> dict[str, str]:
    return {finding.finding_id: f'n{index}' for index, finding in enumerate(ledger.findings)}


def list_retired(ledger: CaseLedger) -> set[str]:
    finding_ids = {finding.finding_id for finding in ledger.findings}
    return {
        finding_id
        for finding in ledger.findings
        for finding_id in finding.supersedes
        if finding_id in finding_ids
    }


def list_threads(ledger: CaseLedger) -> list[str | None]:
    found = {finding.thread for finding in ledger.findings}
    main = [None] * (None in found)
    return [*main, *sorted((thread for thread in found if thread is not None), key=order_thread)]


class TestCaseMapProperties:
    specs = st.builds(
        FindingSpec,
        thread=st.sampled_from((None, 'T1', 'T2', 'T3', 'T10', 'T11')),
        kind=st.sampled_from(FINDING_KINDS),
        text=st.text(max_size=60),
        retires=st.builds(tuple, st.lists(st.integers(min_value=0, max_value=20), max_size=3)),
        dangling=st.booleans(),
    )
    ledgers = st.lists(specs, max_size=14).map(create_threaded_ledger)

    @given(ledger=ledgers)
    def test_each_thread_with_findings_is_one_subgraph_main_first_then_in_numeric_order(
        self, ledger: CaseLedger
    ) -> None:
        drawn = read_map(create_case_map(ledger).render())

        assert list(drawn.titles) == [thread_title(thread) for thread in list_threads(ledger)]
        assert len(set(drawn.subgraph_ids)) == len(drawn.subgraph_ids)

    @given(ledger=ledgers)
    def test_each_finding_is_one_node_named_by_its_index_inside_its_threads_subgraph(
        self, ledger: CaseLedger
    ) -> None:
        drawn = read_map(create_case_map(ledger).render())

        names = list_names(ledger)
        nodes = {node.name: node for node in drawn.nodes}
        assert len(drawn.nodes) == len(ledger.findings)
        assert set(nodes) == set(names.values())
        for finding in ledger.findings:
            node = nodes[names[finding.finding_id]]
            assert node.label.startswith(f'{finding.finding_id} {finding.kind}: ')
            assert node.thread_title == thread_title(finding.thread)

    @given(ledger=ledgers)
    def test_a_node_takes_the_retired_class_exactly_when_a_later_finding_supersedes_it(
        self, ledger: CaseLedger
    ) -> None:
        drawn = read_map(create_case_map(ledger).render())

        names = list_names(ledger)
        retired = list_retired(ledger)
        styles = {node.name: node.style for node in drawn.nodes}
        for finding in ledger.findings:
            expected = 'k_retired' if finding.finding_id in retired else f'k_{finding.kind}'
            assert styles[names[finding.finding_id]] == expected

    @given(ledger=ledgers)
    def test_consecutive_findings_of_a_thread_are_linked_and_nothing_else_is(
        self, ledger: CaseLedger
    ) -> None:
        drawn = read_map(create_case_map(ledger).render())

        names = list_names(ledger)
        expected = []
        for thread in list_threads(ledger):
            members = [names[e.finding_id] for e in ledger.findings if e.thread == thread]
            expected.extend(pairwise(members))
        assert sorted(drawn.links) == sorted(expected)

    @given(ledger=ledgers)
    def test_each_supersedes_finding_id_that_exists_is_one_retirement_edge_from_the_superseder(
        self, ledger: CaseLedger
    ) -> None:
        drawn = read_map(create_case_map(ledger).render())

        names = list_names(ledger)
        expected = [
            (names[finding.finding_id], names[finding_id])
            for finding in ledger.findings
            for finding_id in finding.supersedes
            if finding_id in names
        ]
        assert sorted(drawn.retirements) == sorted(expected)
        assert all(DANGLING_REF not in line for line in create_case_map(ledger).render())

    @given(ledger=ledgers)
    def test_every_line_is_a_subgraph_a_node_a_link_a_retirement_or_an_end(
        self, ledger: CaseLedger
    ) -> None:
        lines = create_case_map(ledger).render()

        assert read_map(lines).strays == ()

    @given(ledger=ledgers)
    @example(ledger=create_threaded_ledger([FindingSpec(thread=None, kind='open', text=HOSTILE)]))
    def test_no_finding_text_adds_a_line_or_a_character_the_label_may_not_hold(
        self, ledger: CaseLedger
    ) -> None:
        lines = create_case_map(ledger).render()

        drawn = read_map(lines)
        assert drawn.strays == ()
        assert all(LABEL_CHARACTERS.fullmatch(node.label) for node in drawn.nodes)
        assert len(drawn.nodes) == len(ledger.findings)
        assert len(lines) == len(drawn.nodes) + len(drawn.titles) * 2 + len(drawn.links) + len(
            drawn.retirements
        )

    def test_an_empty_ledger_draws_nothing(self) -> None:
        assert create_case_map(CaseLedger()).render() == ()


class TestLabelNode:
    safe_words = st.text(alphabet=SAFE_CHARACTERS, min_size=1, max_size=6)
    safe_texts = st.lists(safe_words, min_size=1, max_size=3).map(' '.join)

    def create(
        self, text: str, *, thread: str | None = None, kind: FindingKind = 'known'
    ) -> CaseFinding:
        return create_finding(finding_number=3, thread=thread, kind=kind, text=text)

    @given(
        text=safe_texts, kind=st.sampled_from(FINDING_KINDS), thread=st.sampled_from((None, 'T2'))
    )
    def test_a_short_text_of_allowed_characters_is_kept_whole_after_the_finding_id_and_kind(
        self, text: str, kind: FindingKind, thread: str | None
    ) -> None:
        finding = self.create(text, thread=thread, kind=kind)

        assert label_node(finding) == f'{finding.finding_id} {kind}: {text}'

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
