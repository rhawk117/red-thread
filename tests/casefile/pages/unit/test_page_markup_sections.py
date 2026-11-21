"""HtmlWriter: the facts, the section header, the map and the retired fold."""

from typing import TYPE_CHECKING

from red_thread_casefile.pages import HtmlWriter
from red_thread_casefile.views import Document, Fact, Item, Section

from tests.casefile.pages.builders import PLAIN_URL
from tests.casefile.pages.html_reading import (
    find_tags,
    list_chip_groups,
    list_code_spans,
    list_facts,
    list_item_refs,
    list_section_titles,
    list_sections,
)

if TYPE_CHECKING:
    from tests.casefile.pages.html_reading import SectionReading

RETIRED = 'Retired'


def render(document: Document) -> str:
    return HtmlWriter(document=document).render()


def create_threaded(count: int, first: int = 1) -> tuple[Item, ...]:
    return tuple(
        Item(text=f'claim {number}', ref=f'e{number}', kind='open')
        for number in range(first, first + count)
    )


def read_one_section(section: Section) -> SectionReading:
    (found,) = list_sections(render(Document(title='t', sections=(section,))))
    return found


class TestFacts:
    def test_facts_are_one_list_in_the_given_order_before_the_sections(self) -> None:
        facts = (Fact(label='Bar', value='b'), Fact(label='Kind', value='k'))
        document = Document(title='t', facts=facts, sections=(Section(title='S', prose=('p',)),))

        page = render(document)

        assert [(fact.label, fact.value) for fact in list_facts(page)] == [
            ('Bar', 'b'),
            ('Kind', 'k'),
        ]
        assert page.count('<dl class="facts">') == 1
        assert page.index('class="facts"') < page.index('<h2>S</h2>')

    def test_no_facts_leave_no_list(self) -> None:
        page = render(Document(title='t'))

        assert list_facts(page) == []
        assert find_tags(page, 'dl') == []

    def test_a_wide_fact_is_marked_wide_and_a_narrow_one_is_not(self) -> None:
        facts = (Fact(label='Bar', value='b', wide=True), Fact(label='Kind', value='k'))

        page = render(Document(title='t', facts=facts))

        assert [fact.wide for fact in list_facts(page)] == [True, False]

    def test_a_url_value_is_a_link_and_a_plain_value_is_not(self) -> None:
        facts = (Fact(label='Page', value=PLAIN_URL), Fact(label='Kind', value='root-cause'))

        page = render(Document(title='t', facts=facts))

        assert [fact.link for fact in list_facts(page)] == [PLAIN_URL, None]

    def test_a_backtick_span_in_a_value_is_code(self) -> None:
        page = render(Document(title='t', facts=(Fact(label='Bar', value='name `a.py:3` now'),)))

        assert list_code_spans(page) == ['a.py:3']
        assert list_facts(page)[0].value == 'name a.py:3 now'


class TestSectionHeader:
    def test_a_section_of_entries_shows_its_count_note_and_kind(self) -> None:
        section = Section(title='Open', items=create_threaded(3), kind='open', note='Not settled.')

        found = read_one_section(section)

        assert (found.title, found.count, found.note) == ('Open', 3, 'Not settled.')
        assert found.attributes['data-kind'] == 'open'

    def test_a_section_without_entries_refs_shows_no_count(self) -> None:
        plain = Section(title='Pointers', items=(Item(text='a pointer'),))

        found = read_one_section(plain)

        assert found.count is None

    def test_a_prose_section_shows_no_count_note_or_kind(self) -> None:
        found = read_one_section(Section(title='Goal', prose=('why',)))

        assert (found.count, found.note) == (None, None)
        assert 'data-kind' not in found.attributes

    def test_a_section_is_open_unless_folded(self) -> None:
        open_one = read_one_section(Section(title='A', prose=('x',)))
        folded = read_one_section(Section(title='B', prose=('x',), folded=True))

        assert 'open' in open_one.attributes
        assert 'open' not in folded.attributes


class TestMapAndRetiredFold:
    map_lines = ('n0["e1 open: a"]',)

    def test_the_map_is_a_section_with_a_note_and_no_count_or_kind(self) -> None:
        page = render(Document(title='t', map_lines=self.map_lines))

        (found,) = list_sections(page)
        assert (found.title, found.count) == ('Map', None)
        assert found.note
        assert 'data-kind' not in found.attributes

    def test_the_retired_fold_follows_the_map_is_closed_and_counts_its_entries(self) -> None:
        document = Document(
            title='t',
            sections=(Section(title='Open', items=create_threaded(1)),),
            map_lines=self.map_lines,
            retired=create_threaded(2, first=5),
        )

        page = render(document)

        assert list_section_titles(page) == ['Open', 'Map', RETIRED]
        fold = list_sections(page)[-1]
        assert (fold.count, 'open' in fold.attributes, bool(fold.note)) == (2, False, True)
        assert list_item_refs(fold.body) == ['e5', 'e6']

    def test_no_retired_entry_leaves_no_fold(self) -> None:
        page = render(
            Document(title='t', sections=(Section(title='Open', items=create_threaded(1)),))
        )

        assert RETIRED not in list_section_titles(page)

    def test_retired_entries_are_not_counted_by_the_filter_chips(self) -> None:
        sections = (
            Section(title='Open', items=create_threaded(2)),
            Section(title='Decided', items=(Item(text='d', ref='e3', kind='decision'),)),
        )
        retired = Item(text='gone', ref='e9', kind='known', thread='T1')

        page = render(Document(title='t', sections=sections, retired=(retired,)))

        (kinds,) = list_chip_groups(page)
        assert [(chip.group, chip.value, chip.count) for chip in kinds] == [
            ('kind', 'decision', 1),
            ('kind', 'open', 2),
        ]
