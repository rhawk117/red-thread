"""HtmlPage layout: the rail beside the sections, the columns, the contents and the terms."""

import re

from red_thread_core.documents import Document, Link, Paragraph, Section, Term, parse_line
from red_thread_core.writers.markdown import MarkdownWriter
from red_thread_core.writers.page import HtmlPage

from tests.casefile.pages.html_reading import find_tags

COLUMNS = re.compile(r'<div class="columns">(.*?)</div>\n(?=<details|</main>)', re.DOTALL)
SECTION_TITLE = re.compile(r'<h2>(.*?)</h2>')
RAIL = re.compile(r'<aside class="rail">(.*?)</aside>', re.DOTALL)
CONTENT = re.compile(r'<main class="content">(.*?)</main>', re.DOTALL)


def create_section(title: str, *, column: bool = False) -> Section:
    return Section(title=title, blocks=(Paragraph(line=parse_line(title)),), column=column)


def render(document: Document) -> str:
    return HtmlPage(document=document).render()


def list_column_titles(page: str) -> list[list[str]]:
    return [SECTION_TITLE.findall(group) for group in COLUMNS.findall(page)]


def read_region(pattern: re.Pattern[str], page: str) -> str:
    found = pattern.search(page)
    assert found is not None
    return found[1]


class TestColumns:
    def test_side_by_side_sections_share_one_column_row_and_a_wide_one_breaks_it(self) -> None:
        sections = (
            create_section('Approach'),
            create_section('core', column=True),
            create_section('docs', column=True),
            create_section('Risks'),
            create_section('web', column=True),
        )

        page = render(Document(title='t', sections=sections))

        assert list_column_titles(page) == [['core', 'docs'], ['web']]
        assert SECTION_TITLE.findall(page) == ['Approach', 'core', 'docs', 'Risks', 'web']

    def test_a_page_without_column_sections_has_no_column_row(self) -> None:
        page = render(Document(title='t', sections=(create_section('Approach'),)))

        assert list_column_titles(page) == []


class TestRail:
    terms = (Term(word='worktree', meaning='one git worktree'), Term(word='ref', meaning='C1.e4'))

    def test_the_title_facts_and_controls_sit_in_the_rail_and_the_sections_beside_it(
        self,
    ) -> None:
        sections = (create_section('Approach'), create_section('Risks'))

        page = render(Document(title='The plan', sections=sections, terms=self.terms))

        rail = read_region(RAIL, page)
        assert '<h1>The plan</h1>' in rail
        assert 'class="toolbar"' in rail
        assert SECTION_TITLE.findall(read_region(CONTENT, page)) == ['Approach', 'Risks']

    def test_the_contents_link_each_section_by_its_anchor(self) -> None:
        sections = (create_section('Approach'), create_section('Non-goals'))

        page = render(Document(title='t', sections=sections, appendix=(create_section('Map'),)))

        links = [link['href'] for link in find_tags(read_region(RAIL, page), 'a')]
        anchors = [section['id'] for section in find_tags(page, 'details')]
        assert links == ['#section-approach', '#section-non-goals', '#section-map']
        assert [f'#{anchor}' for anchor in anchors] == links

    def test_one_section_needs_no_contents(self) -> None:
        page = render(Document(title='t', sections=(create_section('Approach'),)))

        assert find_tags(read_region(RAIL, page), 'a') == []

    def test_the_terms_fold_in_the_rail_each_word_with_its_meaning(self) -> None:
        page = render(Document(title='t', terms=self.terms))

        rail = read_region(RAIL, page)
        assert find_tags(rail, 'details') == [{'class': 'terms'}]
        assert re.findall(r'<dt>(.*?)</dt>\s*<dd>(.*?)</dd>', rail) == [
            ('worktree', 'one git worktree'),
            ('ref', 'C1.e4'),
        ]

    def test_a_page_without_terms_has_no_terms_fold(self) -> None:
        page = render(Document(title='t'))

        assert 'class="terms"' not in page


class TestLinks:
    link = Link(url='../plans/p1/plan.html', label='ship it')

    def test_a_labelled_link_shows_its_label_on_the_page(self) -> None:
        section = Section(title='s', blocks=(Paragraph(line=(self.link,)),))

        page = render(Document(title='t', sections=(section,)))

        assert '<a href="../plans/p1/plan.html" rel="noreferrer">ship it</a>' in page

    def test_a_labelled_link_is_a_markdown_link_and_a_bare_one_its_url(self) -> None:
        bare = Link(url='https://example.invalid/a')
        section = Section(title='s', blocks=(Paragraph(line=(self.link, bare)),))

        text = MarkdownWriter(document=Document(title='t', sections=(section,))).render()

        assert '[ship it](../plans/p1/plan.html)https://example.invalid/a' in text.splitlines()
