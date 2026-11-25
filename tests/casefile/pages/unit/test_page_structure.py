"""The page's structure: sections, entry marks, diagrams, the map and the toolbar."""

from dataclasses import dataclass

import pytest
from red_thread_casefile.assets import read_asset
from red_thread_casefile.pages import HtmlWriter
from red_thread_casefile.views import Document, Item, Section

from tests.casefile.pages.builders import DIAGRAM, create_document, create_marked_item
from tests.casefile.pages.html_reading import (
    find_buttons,
    find_entries,
    find_tags,
    list_chip_groups,
    list_mermaid,
    list_section_titles,
)
from tests.params import as_params

MAP_LINES = ('  subgraph main["main ledger"]', '    n0["e1 known: a claim"]:::k_known', '  end')


def render(document: Document) -> str:
    return HtmlWriter(document=document).render()


@dataclass(slots=True, kw_only=True, frozen=True)
class ChipRule:
    name: str
    items: tuple[Item, ...]
    groups: tuple[str, ...]
    marks: tuple[pytest.MarkDecorator, ...] = ()


def chip_rule_cases() -> pytest.MarkDecorator:
    rules = [
        ChipRule(name='no-entry', items=(Item(text='a pointer'),), groups=()),
        ChipRule(
            name='one-kind-and-one-thread',
            items=(create_marked_item(ref='e1'), create_marked_item(ref='e2')),
            groups=(),
        ),
        ChipRule(
            name='two-kinds-and-one-thread',
            items=(create_marked_item(ref='e1'), create_marked_item(ref='e2', kind='open')),
            groups=('kind',),
        ),
        ChipRule(
            name='one-kind-and-two-threads',
            items=(create_marked_item(ref='e1'), create_marked_item(ref='T1.e1', thread='T1')),
            groups=('thread',),
        ),
        ChipRule(
            name='two-kinds-and-two-threads',
            items=(
                create_marked_item(ref='e1'),
                create_marked_item(ref='T1.e1', kind='open', thread='T1'),
            ),
            groups=('kind', 'thread'),
        ),
    ]
    return pytest.mark.parametrize('rule', as_params(rules))


class TestSections:
    def test_a_section_is_an_open_details_with_its_title_as_a_heading_in_its_summary(self) -> None:
        document = Document(
            title='t',
            sections=(Section(title='First', prose=('a',)), Section(title='Second', prose=('b',))),
        )

        page = render(document)

        assert find_tags(page, 'details') == [{'class': 'section', 'open': ''}] * 2
        assert list_section_titles(page) == ['First', 'Second']


class TestEntryMarks:
    def test_an_item_with_a_ref_carries_its_kind_and_thread(self) -> None:
        page = render(create_document(create_marked_item(ref='T1.e2', kind='open', thread='T1')))

        assert find_entries(page) == [{'class': 'entry', 'data-kind': 'open', 'data-thread': 'T1'}]

    def test_a_missing_kind_and_the_main_ledger_are_empty_strings(self) -> None:
        page = render(create_document(create_marked_item(kind=None, thread=None)))

        assert find_entries(page) == [{'class': 'entry', 'data-kind': '', 'data-thread': ''}]

    def test_an_item_with_no_ref_carries_no_mark_and_no_ref_button(self) -> None:
        page = render(create_document(Item(text='a pointer', kind='known', thread='T1')))

        assert find_entries(page) == [{'class': 'entry'}]
        assert find_buttons(page, 'ref') == []

    def test_the_ref_is_a_button_that_copies_it(self) -> None:
        page = render(create_document(create_marked_item(ref='T1.e2', thread='T1')))

        (button,) = find_buttons(page, 'ref')
        assert button['type'] == 'button'
        assert button['data-copy'] == 'T1.e2'


class TestDiagrams:
    def test_an_item_diagram_is_a_pre_mermaid_element_with_its_source_escaped(self) -> None:
        item = Item(text='a claim', ref='e1', diagram=DIAGRAM)

        page = render(create_document(item))

        assert list_mermaid(page) == [DIAGRAM]
        assert find_tags(page, 'pre') == [{'class': 'mermaid'}]
        assert 'B --&gt; C' in page
        assert 'B --> C' not in page

    def test_an_item_with_no_diagram_has_no_pre_element(self) -> None:
        page = render(create_document(Item(text='a claim', ref='e1')))

        assert find_tags(page, 'pre') == []
        assert list_mermaid(page) == []


class TestMap:
    def test_map_lines_end_the_page_in_a_map_section_holding_the_map_header_and_the_lines(
        self,
    ) -> None:
        item = Item(text='a claim', ref='e1', diagram=DIAGRAM)
        document = Document(title='t', sections=create_document(item).sections, map_lines=MAP_LINES)

        page = render(document)

        assert list_section_titles(page) == ['Findings', 'Map']
        assert find_tags(page, 'details') == [{'class': 'section', 'open': ''}] * 2
        diagram, drawn = list_mermaid(page)
        assert diagram == DIAGRAM
        assert drawn.splitlines() == [*read_asset('map.mmd').splitlines(), *MAP_LINES]

    def test_no_map_lines_leave_no_map_section(self) -> None:
        page = render(create_document(create_marked_item()))

        assert 'Map' not in list_section_titles(page)
        assert list_mermaid(page) == []

    def test_a_document_with_only_map_lines_still_draws_the_map(self) -> None:
        page = render(Document(title='t', map_lines=MAP_LINES))

        assert list_section_titles(page) == ['Map']
        assert len(list_mermaid(page)) == 1


class TestToolbar:
    def test_a_document_with_no_section_has_no_toolbar(self) -> None:
        page = render(Document(title='t', summary=('a line',)))

        assert find_tags(page, 'nav') == []
        assert find_buttons(page, 'tool') == []

    def test_a_document_with_sections_but_no_entry_has_only_the_fold_button(self) -> None:
        page = render(Document(title='t', sections=(Section(title='s', prose=('a',)),)))

        assert find_tags(page, 'nav') == [{'class': 'toolbar', 'aria-label': 'Page controls'}]
        assert list_chip_groups(page) == []
        (tool,) = find_buttons(page, 'tool')
        assert 'data-fold' in tool

    def test_the_toolbar_comes_before_the_first_section(self) -> None:
        page = render(create_document(create_marked_item()))

        assert page.index('class="toolbar"') < page.index('<details')

    @chip_rule_cases()
    def test_a_filter_gets_a_chip_group_only_when_it_has_two_or_more_chips(
        self, rule: ChipRule
    ) -> None:
        page = render(create_document(*rule.items))

        assert sorted(group[0].group for group in list_chip_groups(page)) == list(rule.groups)
        assert all(len(group) >= 2 for group in list_chip_groups(page))
