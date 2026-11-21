"""The rendered page's promise: two pinned CDN scripts, its own inline script and styles."""

import re
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.pages import HtmlWriter
from red_thread_casefile.views import Document, Item, Section

from tests.casefile.pages.html_reading import (
    MERMAID_URL,
    TAILWIND_URL,
    list_scripts,
    list_styles,
    list_tag_names,
)
from tests.casefile.pages.promises import TAILWIND_STYLE, assert_page_holds_only_its_own_markup

if TYPE_CHECKING:
    from tests.casefile.pages.html_reading import Element

CDN_SCRIPT = re.compile(
    r'https://cdnjs\.cloudflare\.com/ajax/libs/[\w.-]+/\d+\.\d+\.\d+/[\w.-]+\.js'
)
INTEGRITY = re.compile(r'sha512-[A-Za-z0-9+/]+={0,2}')
OUTSIDE_URL = re.compile(r'https?://[^\s"\'<>)]+')
PLACEHOLDER = re.compile(r'\$\w+')


def create_rich_document() -> Document:
    item = Item(
        text='a claim with `code`',
        ref='e1',
        cite='src/queue.py:3',
        notes=('rests on: a page',),
        flags=('citation changed',),
        kind='known',
        thread='T1',
        diagram='flowchart TD\n  A --> B',
    )
    other = Item(text='a question', ref='e2', kind='open')
    section = Section(title='Findings', items=(item, other), prose=('a line of prose',))
    map_lines = ('  subgraph main["main ledger"]', '    n0["e1 known: a claim"]:::k_known', '  end')
    return Document(
        title='A case', summary=('Case line',), sections=(section,), map_lines=map_lines
    )


def render_rich_page() -> str:
    return HtmlWriter(document=create_rich_document()).render()


def render_empty_page() -> str:
    return HtmlWriter(document=Document(title='Nothing yet')).render()


def page_cases() -> pytest.MarkDecorator:
    pages = {'with-entries-and-a-map': render_rich_page(), 'with-nothing': render_empty_page()}
    return pytest.mark.parametrize(
        'page', [pytest.param(page, id=name) for name, page in pages.items()]
    )


class TestPagePromise:
    @page_cases()
    def test_the_page_holds_only_the_writers_elements_scripts_and_styles(self, page: str) -> None:
        assert_page_holds_only_its_own_markup(page)

    @page_cases()
    def test_the_page_is_one_html_document(self, page: str) -> None:
        assert page.startswith('<!doctype html>')
        assert page.rstrip().endswith('</html>')
        assert page.count('<html') == 1

    @page_cases()
    def test_exactly_two_scripts_come_from_cdnjs_at_an_exact_version_with_integrity(
        self, page: str
    ) -> None:
        external = [script for script in list_scripts(page) if 'src' in script.attributes]

        assert sorted(script.attributes['src'] for script in external) == sorted([
            TAILWIND_URL,
            MERMAID_URL,
        ])
        assert all(CDN_SCRIPT.fullmatch(script.attributes['src']) for script in external)
        assert all(INTEGRITY.fullmatch(script.attributes['integrity']) for script in external)
        assert all(script.attributes['crossorigin'] == 'anonymous' for script in external)
        assert all(script.body == '' for script in external)

    @page_cases()
    def test_tailwind_loads_in_the_head_and_mermaid_at_the_end_of_the_body(self, page: str) -> None:
        assert page.index(TAILWIND_URL) < page.index('</head>')
        assert page.index('<body>') < page.index('</main>') < page.index(MERMAID_URL)
        assert page.index(MERMAID_URL) < page.index('</body>')

    @page_cases()
    def test_exactly_one_inline_script_and_it_is_the_script_asset(self, page: str) -> None:
        inline = [script for script in list_scripts(page) if 'src' not in script.attributes]

        assert len(inline) == 1
        assert inline[0].body.strip() != ''

    @page_cases()
    def test_the_two_styles_are_the_plain_one_and_the_tailwind_one(self, page: str) -> None:
        styles = list_styles(page)

        kinds = sorted(style.attributes.get('type', '') for style in styles)
        assert kinds == ['', TAILWIND_STYLE]
        assert all('@import' not in style.body for style in styles)

    @page_cases()
    def test_nothing_else_is_pulled_in_from_outside(self, page: str) -> None:
        assert 'link' not in list_tag_names(page)
        assert 'url(' not in page.lower()
        assert sorted(OUTSIDE_URL.findall(page)) == sorted([TAILWIND_URL, MERMAID_URL])

    @page_cases()
    def test_no_placeholder_of_the_skeleton_survives(self, page: str) -> None:
        assert PLACEHOLDER.findall(page) == []

    @page_cases()
    def test_the_inline_script_is_not_cut_short(self, page: str) -> None:
        bodies: list[Element] = list_scripts(page)

        assert sum(body.body.lower().count('</script') for body in bodies) == 0
