"""HtmlWriter: what one item shows, its verdict, citation state, quote and stamps."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.domain import VERDICTS
from red_thread_casefile.pages import HtmlWriter
from red_thread_casefile.policy import CITE_STATES, Finding
from red_thread_casefile.views import Item

from tests.casefile.pages.builders import PLAIN_URL, create_document
from tests.casefile.pages.html_reading import (
    find_tags,
    list_cite_blocks,
    list_cited_quotes,
    list_claim_markup,
    list_flags,
    list_note_rows,
    list_quotes,
    list_spans,
)

if TYPE_CHECKING:
    from red_thread_casefile.domain import Verdict
    from red_thread_casefile.policy import CiteState

PATH = 'src/queue.py:3'
MOMENT = '2026-11-21T09:30:00+00:00'
TWO_LINES = '    time.sleep(job.delay)\n    return job.run()'


def render_item(item: Item) -> str:
    return HtmlWriter(document=create_document(item)).render()


def create_finding(state: CiteState, moved_to: int | None = None) -> Finding:
    return Finding(ref='e1', cite=PATH, state=state, moved_to=moved_to)


def verdict_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('verdict', [pytest.param(v, id=v) for v in VERDICTS])


def state_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('state', [pytest.param(s, id=s) for s in CITE_STATES])


class TestVerdictBadge:
    @verdict_cases()
    def test_a_verdict_is_a_badge_that_starts_the_claim(self, verdict: Verdict) -> None:
        page = render_item(Item(text='maybe so', verdict=verdict))

        (badge,) = list_spans(page, 'verdict')
        assert (badge.body, badge.attributes) == (
            verdict,
            {'class': 'verdict', 'data-verdict': verdict},
        )
        assert list_claim_markup(page) == [
            f'<span class="verdict" data-verdict="{verdict}">{verdict}</span> maybe so'
        ]

    def test_no_verdict_leaves_the_claim_bare(self) -> None:
        page = render_item(Item(text='maybe so'))

        assert list_spans(page, 'verdict') == []
        assert list_claim_markup(page) == ['maybe so']


class TestCitationState:
    @state_cases()
    def test_each_state_is_a_badge_labelled_with_it(self, state: CiteState) -> None:
        page = render_item(Item(text='a', cite=PATH, finding=create_finding(state)))

        (badge,) = list_spans(page, 'state')
        assert (badge.body, badge.attributes['data-state']) == (state, state)

    def test_a_moved_citation_names_the_line_it_moved_to(self) -> None:
        page = render_item(Item(text='a', cite=PATH, finding=create_finding('moved', 4)))

        (badge,) = list_spans(page, 'state')
        assert (badge.body, badge.attributes['data-state']) == ('moved to line 4', 'moved')

    def test_a_moved_citation_with_no_line_is_just_moved(self) -> None:
        page = render_item(Item(text='a', cite=PATH, finding=create_finding('moved')))

        (badge,) = list_spans(page, 'state')
        assert badge.body == 'moved'

    def test_the_badge_sits_in_the_cite_line_before_the_copy_button(self) -> None:
        page = render_item(Item(text='a', cite=PATH, finding=create_finding('changed')))

        (block,) = list_cite_blocks(page)
        assert block.index('class="state"') < block.index('class="copy"')

    def test_a_url_cite_carries_its_badge_too(self) -> None:
        finding = Finding(ref='e1', cite=PLAIN_URL, state='unchecked')

        page = render_item(Item(text='a', cite=PLAIN_URL, finding=finding))

        assert [span.body for span in list_spans(page, 'state')] == ['unchecked']

    def test_no_finding_means_no_badge(self) -> None:
        page = render_item(Item(text='a', cite=PATH))

        assert list_spans(page, 'state') == []

    def test_a_finding_without_a_cite_shows_nothing(self) -> None:
        page = render_item(Item(text='a', finding=create_finding('missing')))

        assert list_spans(page, 'state') == []

    @state_cases()
    def test_a_state_never_becomes_a_flag(self, state: CiteState) -> None:
        page = render_item(Item(text='a', cite=PATH, finding=create_finding(state)))

        assert list_flags(page) == []


class TestQuote:
    def test_a_path_cite_shows_its_quote_after_the_cite_line_with_its_lines_kept(self) -> None:
        page = render_item(Item(text='a', cite=PATH, quote=TWO_LINES))

        assert list_cited_quotes(page) == [TWO_LINES]
        assert find_tags(page, 'pre') == [{'class': 'quote'}]

    def test_no_quote_means_no_quote_element(self) -> None:
        assert list_quotes(render_item(Item(text='a', cite=PATH))) == []

    def test_a_quote_with_no_cite_shows_nothing(self) -> None:
        assert list_quotes(render_item(Item(text='a', quote=TWO_LINES))) == []


class TestStamps:
    def test_the_round_and_the_day_are_the_first_notes_and_the_time_is_kept_whole(self) -> None:
        item = Item(
            text='a', round=2, at=MOMENT, flags=('lead, recorded at 1111111',), notes=('n',)
        )

        page = render_item(item)

        (row,) = list_note_rows(page)
        assert row == [
            ('stamp', 'round 2'),
            ('stamp', '2026-11-21'),
            ('flag', 'lead, recorded at 1111111'),
            ('', 'n'),
        ]
        assert find_tags(page, 'time') == [{'datetime': MOMENT}]

    def test_round_zero_is_still_a_stamp(self) -> None:
        (row,) = list_note_rows(render_item(Item(text='a', round=0)))

        assert row == [('stamp', 'round 0')]

    def test_a_round_alone_and_a_time_alone_each_show_one_stamp(self) -> None:
        (only_round,) = list_note_rows(render_item(Item(text='a', round=3)))
        (only_time,) = list_note_rows(render_item(Item(text='a', at=MOMENT)))

        assert only_round == [('stamp', 'round 3')]
        assert only_time == [('stamp', '2026-11-21')]

    def test_an_item_with_no_stamp_flag_or_note_has_no_note_list(self) -> None:
        assert list_note_rows(render_item(Item(text='a'))) == []
