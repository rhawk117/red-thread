"""The page templates: each compiles, reads only what it is given, and every block has one."""

import re
from typing import TYPE_CHECKING

import pytest
from jinja2 import meta
from red_thread_casefile.documents import EntryList
from red_thread_core.documents import (
    CodeListing,
    Document,
    Flowchart,
    Link,
    Paragraph,
    PointList,
    Section,
    parse_line,
)
from red_thread_core.packaged import read_asset
from red_thread_core.writers.page import PAGE_TEMPLATE

from tests.casefile.documents.builders import create_entry_node
from tests.casefile.pages.html_reading import MERMAID_URL, TAILWIND_URL
from tests.casefile.writers.reading import load_page_environment, render_page
from tests.params import as_labelled_params

if TYPE_CHECKING:
    from red_thread_core.documents import Block
    from red_thread_core.packaged import CoreAsset

TEMPLATE_SUFFIX = '.html.j2'
BLOCK_FOLDER = 'blocks/'
INCLUDED_ASSETS: tuple[CoreAsset, ...] = ('page.css', 'tailwind.css', 'page.js')
HOSTILE_URL = 'javascript:alert(1)'
OUTSIDE_URL = re.compile(r'https?://[^\s"\'<>)]+')


def is_template(name: str) -> bool:
    return name.endswith(TEMPLATE_SUFFIX)


def list_template_names() -> list[str]:
    return load_page_environment().list_templates(filter_func=is_template)


def read_source(name: str) -> str:
    environment = load_page_environment()
    loader = environment.loader
    assert loader is not None
    source, _, _ = loader.get_source(environment, name)
    return source


def find_names(name: str) -> set[str]:
    environment = load_page_environment()
    return meta.find_undeclared_variables(environment.parse(read_source(name)))


def template_cases() -> pytest.MarkDecorator:
    names = list_template_names()
    return pytest.mark.parametrize('name', [pytest.param(name, id=name) for name in names])


def block_template_cases() -> pytest.MarkDecorator:
    names = [name for name in list_template_names() if name.startswith(BLOCK_FOLDER)]
    return pytest.mark.parametrize('name', [pytest.param(name, id=name) for name in names])


def block_cases() -> pytest.MarkDecorator:
    blocks: dict[str, Block] = {
        'paragraph': Paragraph(line=parse_line('a `b`')),
        'points': PointList(points=(parse_line('a'),)),
        'flowchart': Flowchart(lines=('flowchart TD', '  A --> B')),
        'listing': CodeListing(language='python', source='pass'),
        'entries': EntryList(entries=(create_entry_node(),)),
    }
    return pytest.mark.parametrize('block', as_labelled_params(blocks))


def included_asset_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        'name', [pytest.param(name, id=name) for name in INCLUDED_ASSETS]
    )


class TestTemplates:
    @template_cases()
    def test_a_template_compiles(self, name: str) -> None:
        assert load_page_environment().get_template(name).name == name

    def test_the_page_reads_only_the_page(self) -> None:
        assert find_names(PAGE_TEMPLATE) == {'page'}

    def test_the_page_names_no_outside_url_but_the_two_pinned_scripts(self) -> None:
        found = OUTSIDE_URL.findall(read_source(PAGE_TEMPLATE))

        assert sorted(found) == sorted((TAILWIND_URL, MERMAID_URL))

    @block_template_cases()
    def test_a_block_template_reads_only_its_block(self, name: str) -> None:
        assert find_names(name) == {'block'}

    @block_cases()
    def test_every_block_has_a_template_that_draws_it(self, block: Block) -> None:
        assert load_page_environment().get_template(block.template).render(block=block)


class TestPage:
    @pytest.fixture
    def page(self) -> str:
        return render_page(Document(title='t'))

    @included_asset_cases()
    def test_the_page_carries_each_asset_as_written(self, page: str, name: CoreAsset) -> None:
        assert read_asset(name) in page

    def test_a_link_that_is_not_to_the_web_keeps_its_text_and_loses_its_target(self) -> None:
        line = (Link(url=HOSTILE_URL, label='docs'),)
        page = render_page(
            Document(title='t', sections=(Section(title='s', blocks=(Paragraph(line=line),)),))
        )

        assert HOSTILE_URL not in page
        assert '<a href="" rel="noreferrer">docs</a>' in page
