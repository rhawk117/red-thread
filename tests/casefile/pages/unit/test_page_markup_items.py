"""The page: what one finding shows, its verdict, citation state, quote and stamps."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.documents import CitationNode
from red_thread_casefile.domain import VERDICTS
from red_thread_casefile.packaged import load_wording
from red_thread_casefile.policy import CITE_STATES, CitationCheck
from red_thread_core.documents import Document, PointList, Section, parse_line

from tests.casefile.ledger.memory import MOMENT
from tests.casefile.pages.builders import PLAIN_URL, create_document
from tests.casefile.pages.html_reading import (
    find_tags,
    list_citation_blocks,
    list_cited_quotes,
    list_claim_markup,
    list_flags,
    list_note_rows,
    list_quotes,
    list_spans,
)
from tests.casefile.writers.builders import create_finding_node
from tests.casefile.writers.reading import render_page

if TYPE_CHECKING:
    from red_thread_casefile.documents import FindingNode
    from red_thread_casefile.domain import Verdict
    from red_thread_casefile.policy import CitationState

PATH = 'src/queue.py:3'
TWO_LINES = '    time.sleep(job.delay)\n    return job.run()'
DAY = '2026-11-21'


def render_finding(finding: FindingNode) -> str:
    return render_page(create_document(finding))


def create_citation_check(state: CitationState, moved_to: int | None = None) -> CitationCheck:
    return CitationCheck(finding_id='e1', citation=PATH, state=state, moved_to=moved_to)


def create_cited(citation_node: CitationNode) -> FindingNode:
    return create_finding_node('a').replace_with(citation_node=citation_node)


def create_path_cited(state: CitationState, moved_to: int | None = None) -> FindingNode:
    return create_cited(
        CitationNode(target=PATH, citation_check=create_citation_check(state, moved_to))
    )


def create_stamped(round_number: int) -> FindingNode:
    return create_finding_node('a').replace_with(round=round_number, at=MOMENT)


def verdict_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('verdict', [pytest.param(v, id=v) for v in VERDICTS])


def state_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('state', [pytest.param(s, id=s) for s in CITE_STATES])


class TestVerdictBadge:
    @verdict_cases()
    def test_a_verdict_is_a_badge_that_starts_the_claim(self, verdict: Verdict) -> None:
        page = render_finding(create_finding_node('maybe so').replace_with(verdict=verdict))

        (badge,) = list_spans(page, 'verdict')
        assert (badge.body, badge.attributes) == (
            verdict,
            {'class': 'verdict', 'data-verdict': verdict},
        )
        assert list_claim_markup(page) == [
            f'<span class="verdict" data-verdict="{verdict}">{verdict}</span> maybe so'
        ]

    def test_no_verdict_leaves_the_claim_bare(self) -> None:
        page = render_finding(create_finding_node('maybe so'))

        assert list_spans(page, 'verdict') == []
        assert list_claim_markup(page) == ['maybe so']


class TestCitationState:
    @state_cases()
    def test_each_state_is_a_badge_labelled_with_it(self, state: CitationState) -> None:
        page = render_finding(create_path_cited(state))

        (badge,) = list_spans(page, 'state')
        assert (badge.body, badge.attributes['data-state']) == (state, state)

    def test_a_moved_citation_names_the_line_it_moved_to(self) -> None:
        page = render_finding(create_path_cited('moved', 4))

        (badge,) = list_spans(page, 'state')
        assert (badge.body, badge.attributes['data-state']) == ('moved to line 4', 'moved')

    def test_a_moved_citation_with_no_line_is_just_moved(self) -> None:
        page = render_finding(create_path_cited('moved'))

        (badge,) = list_spans(page, 'state')
        assert badge.body == 'moved'

    def test_the_badge_sits_in_the_citation_line_before_the_copy_button(self) -> None:
        page = render_finding(create_path_cited('changed'))

        (block,) = list_citation_blocks(page)
        assert block.index('class="state"') < block.index('class="copy"')

    def test_a_url_citation_carries_its_badge_too(self) -> None:
        citation_check = CitationCheck(finding_id='e1', citation=PLAIN_URL, state='unchecked')

        page = render_finding(
            create_cited(CitationNode(target=PLAIN_URL, citation_check=citation_check))
        )

        assert [span.body for span in list_spans(page, 'state')] == ['unchecked']

    def test_no_citation_check_means_no_badge(self) -> None:
        page = render_finding(create_cited(CitationNode(target=PATH)))

        assert list_spans(page, 'state') == []

    def test_an_finding_without_a_citation_shows_no_citation_line_and_no_badge(self) -> None:
        page = render_finding(create_finding_node('a'))

        assert list_citation_blocks(page) == []
        assert list_spans(page, 'state') == []

    @state_cases()
    def test_a_state_never_becomes_a_flag(self, state: CitationState) -> None:
        page = render_finding(create_path_cited(state))

        assert list_flags(page) == []


class TestQuote:
    def test_a_path_citation_shows_its_quote_after_the_citation_line_with_its_lines_kept(
        self,
    ) -> None:
        page = render_finding(create_cited(CitationNode(target=PATH, quote=TWO_LINES)))

        assert list_cited_quotes(page) == [TWO_LINES]
        assert find_tags(page, 'pre') == [{'class': 'quote'}]

    def test_no_quote_means_no_quote_element(self) -> None:
        assert list_quotes(render_finding(create_cited(CitationNode(target=PATH)))) == []

    def test_a_url_citation_shows_no_quote(self) -> None:
        page = render_finding(create_cited(CitationNode(target=PLAIN_URL, quote=TWO_LINES)))

        assert list_quotes(page) == []


class TestStamps:
    def test_the_round_and_the_day_are_the_first_notes_and_the_time_is_kept_whole(self) -> None:
        finding = create_stamped(2).replace_with(
            lead='1111111', notes=(load_wording().write_note('source', 'n'),)
        )

        page = render_finding(finding)

        (row,) = list_note_rows(page)
        assert row == [
            ('stamp', 'round 2'),
            ('stamp', DAY),
            ('flag', 'lead, recorded at 1111111'),
            ('', 'n'),
        ]
        assert find_tags(page, 'time') == [{'datetime': MOMENT}]

    def test_round_zero_is_still_a_stamp(self) -> None:
        (row,) = list_note_rows(render_finding(create_stamped(0)))

        assert row == [('stamp', 'round 0'), ('stamp', DAY)]

    def test_an_finding_with_no_flag_or_note_shows_only_its_two_stamps(self) -> None:
        (row,) = list_note_rows(render_finding(create_stamped(3)))

        assert row == [('stamp', 'round 3'), ('stamp', DAY)]

    def test_a_point_has_no_note_list(self) -> None:
        points = PointList(points=(parse_line('a'),))
        document = Document(title='t', sections=(Section(title='Pointers', blocks=(points,)),))

        assert list_note_rows(render_page(document)) == []
