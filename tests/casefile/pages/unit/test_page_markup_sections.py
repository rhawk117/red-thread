"""The page: the facts, the section header, the map and the retired fold."""

from typing import TYPE_CHECKING

from red_thread_casefile.documents import FindingList
from red_thread_casefile.packaged import load_wording, read_asset
from red_thread_core.documents import (
    Document,
    Fact,
    Flowchart,
    Paragraph,
    PointList,
    Section,
    parse_line,
    parse_value,
)

from tests.casefile.pages.html_reading import (
    find_tags,
    list_code_spans,
    list_facts,
    list_finding_id_buttons,
    list_section_titles,
    list_sections,
)
from tests.casefile.writers.builders import create_finding_node
from tests.casefile.writers.reading import render_page

if TYPE_CHECKING:
    from red_thread_casefile.documents import FindingNode

    from tests.casefile.pages.html_reading import SectionReading

RETIRED = 'Retired'


def create_threaded(count: int, first: int = 1) -> tuple[FindingNode, ...]:
    return tuple(
        create_finding_node(f'claim {number}', f'e{number}').replace_with(kind='open')
        for number in range(first, first + count)
    )


def create_open_section(count: int) -> Section:
    return Section(title='Open', blocks=(FindingList(findings=create_threaded(count)),))


def create_prose_section(title: str, *, folded: bool = False) -> Section:
    return Section(title=title, blocks=(Paragraph(line=parse_line('x')),), folded=folded)


def create_map_section(lines: tuple[str, ...]) -> Section:
    chart = Flowchart(lines=(read_asset('map.mmd').rstrip(), *lines))
    return Section(title='Map', blocks=(chart,), note=load_wording().map_note)


def create_retired_section(findings: tuple[FindingNode, ...]) -> Section:
    blocks = (FindingList(findings=findings),)
    return Section(title=RETIRED, blocks=blocks, note=load_wording().retired_note, folded=True)


def read_one_section(section: Section) -> SectionReading:
    (found,) = list_sections(render_page(Document(title='t', sections=(section,))))
    return found


class TestFacts:
    def test_facts_are_one_list_in_the_given_order_before_the_sections(self) -> None:
        facts = (
            Fact(label='Bar', value=parse_value('b')),
            Fact(label='Kind', value=parse_value('k')),
        )
        section = Section(title='S', blocks=(Paragraph(line=parse_line('p')),))
        document = Document(title='t', facts=facts, sections=(section,))

        page = render_page(document)

        assert [(fact.label, fact.value) for fact in list_facts(page)] == [
            ('Bar', 'b'),
            ('Kind', 'k'),
        ]
        assert page.count('<dl class="facts">') == 1
        assert page.index('class="facts"') < page.index('<h2>S</h2>')

    def test_no_facts_leave_no_list(self) -> None:
        page = render_page(Document(title='t'))

        assert list_facts(page) == []
        assert find_tags(page, 'dl') == []

    def test_a_backtick_span_in_a_value_is_code(self) -> None:
        fact = Fact(label='Bar', value=parse_value('name `a.py:3` now'))

        page = render_page(Document(title='t', facts=(fact,)))

        assert list_code_spans(page) == ['a.py:3']
        assert list_facts(page)[0].value == 'name a.py:3 now'


class TestSectionHeader:
    def test_a_section_of_points_shows_no_count(self) -> None:
        points = PointList(points=(parse_line('a pointer'),))

        found = read_one_section(Section(title='Pointers', blocks=(points,)))

        assert found.count is None

    def test_a_prose_section_shows_no_count_note_or_kind(self) -> None:
        found = read_one_section(create_prose_section('Goal'))

        assert (found.count, found.note) == (None, None)
        assert 'data-kind' not in found.attributes

    def test_a_section_is_open_unless_folded(self) -> None:
        open_one = read_one_section(create_prose_section('A'))
        folded = read_one_section(create_prose_section('B', folded=True))

        assert 'open' in open_one.attributes
        assert 'open' not in folded.attributes


class TestMapAndRetiredFold:
    map_lines = ('n0["e1 open: a"]',)

    def test_the_map_is_a_section_with_a_note_and_no_count_or_kind(self) -> None:
        page = render_page(Document(title='t', appendix=(create_map_section(self.map_lines),)))

        (found,) = list_sections(page)
        assert (found.title, found.count) == ('Map', None)
        assert found.note is not None
        assert found.note != ''
        assert 'data-kind' not in found.attributes

    def test_the_retired_fold_follows_the_map_is_closed_and_counts_its_findings(self) -> None:
        appendix = (
            create_map_section(self.map_lines),
            create_retired_section(create_threaded(2, first=5)),
        )
        document = Document(title='t', sections=(create_open_section(1),), appendix=appendix)

        page = render_page(document)

        assert list_section_titles(page) == ['Open', 'Map', RETIRED]
        fold = list_sections(page)[-1]
        assert (fold.count, 'open' in fold.attributes, bool(fold.note)) == (2, False, True)
        assert list_finding_id_buttons(fold.body) == ['e5', 'e6']

    def test_no_retired_finding_leaves_no_fold(self) -> None:
        page = render_page(Document(title='t', sections=(create_open_section(1),)))

        assert RETIRED not in list_section_titles(page)
