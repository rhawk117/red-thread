"""The page assets: the promises that hold for the files themselves, before any case is rendered."""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, get_args

import pytest
from red_thread_casefile.assets import AssetName, read_asset
from red_thread_casefile.domain import ENTRY_KINDS

from tests.casefile.pages.asset_names import ASSET_NAMES
from tests.casefile.pages.html_reading import MERMAID_URL, TAILWIND_URL

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet

OUTSIDE_URL = re.compile(r'https?://[^\s"\'<>)]+')
STYLE_NAMES: tuple[AssetName, ...] = ('page.css', 'tailwind.css')


@dataclass(slots=True, kw_only=True, frozen=True)
class AssetUrls:
    name: AssetName
    urls: tuple[str, ...]

    @property
    def param(self) -> ParameterSet:
        return pytest.param(self, id=self.name)


def asset_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('name', [pytest.param(name, id=name) for name in ASSET_NAMES])


def style_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('name', [pytest.param(name, id=name) for name in STYLE_NAMES])


def asset_url_cases() -> pytest.MarkDecorator:
    pinned = (TAILWIND_URL, MERMAID_URL)
    urls = [
        AssetUrls(name=name, urls=pinned if name == 'page.html' else ()) for name in ASSET_NAMES
    ]
    return pytest.mark.parametrize('scenario', [scenario.param for scenario in urls])


class TestAssetPromises:
    def test_the_asset_names_here_are_the_names_the_reader_takes(self) -> None:
        assert set(get_args(AssetName.__value__)) == set(ASSET_NAMES)

    @asset_cases()
    def test_an_asset_is_read_as_text(self, name: AssetName) -> None:
        assert read_asset(name).strip()

    @asset_url_cases()
    def test_no_asset_names_an_outside_url_but_the_two_pinned_scripts(
        self, scenario: AssetUrls
    ) -> None:
        found = OUTSIDE_URL.findall(read_asset(scenario.name))

        assert sorted(found) == sorted(scenario.urls)

    @asset_cases()
    def test_no_asset_holds_a_link_element_or_a_css_url(self, name: AssetName) -> None:
        text = read_asset(name).lower()

        assert '<link' not in text
        assert 'url(' not in text

    @style_cases()
    def test_no_stylesheet_holds_an_import_comments_included(self, name: AssetName) -> None:
        assert '@import' not in read_asset(name).lower()

    def test_the_script_asset_cannot_close_the_script_element_that_holds_it(self) -> None:
        assert '</script' not in read_asset('page.js').lower()

    def test_the_map_header_styles_every_class_a_map_node_can_take(self) -> None:
        header = read_asset('map.mmd')

        classes = {name for name in (*ENTRY_KINDS, 'retired') if f'classDef k_{name} ' in header}
        assert classes == {*ENTRY_KINDS, 'retired'}

    def test_the_map_header_opens_a_top_down_flowchart(self) -> None:
        assert read_asset('map.mmd').startswith('flowchart TD\n')
