"""The page assets: the promises that hold for the files themselves, before any case is rendered."""

import re
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.domain import ENTRY_KINDS
from red_thread_casefile.packaged import read_asset as read_case_asset
from red_thread_core.packaged import read_asset

from tests.casefile.pages.asset_names import ASSET_NAMES

if TYPE_CHECKING:
    from red_thread_core.packaged import CoreAsset

OUTSIDE_URL = re.compile(r'https?://[^\s"\'<>)]+')
STYLE_NAMES: tuple[CoreAsset, ...] = ('page.css', 'tailwind.css')


def asset_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('name', [pytest.param(name, id=name) for name in ASSET_NAMES])


def style_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('name', [pytest.param(name, id=name) for name in STYLE_NAMES])


class TestAssetPromises:
    @asset_cases()
    def test_an_asset_is_read_as_text(self, name: CoreAsset) -> None:
        assert read_asset(name).strip()

    @asset_cases()
    def test_no_asset_names_an_outside_url(self, name: CoreAsset) -> None:
        assert OUTSIDE_URL.findall(read_asset(name)) == []

    @asset_cases()
    def test_no_asset_holds_a_link_element_or_a_css_url(self, name: CoreAsset) -> None:
        text = read_asset(name).lower()

        assert '<link' not in text
        assert 'url(' not in text

    @style_cases()
    def test_no_stylesheet_holds_an_import_comments_included(self, name: CoreAsset) -> None:
        assert '@import' not in read_asset(name).lower()

    def test_the_script_asset_cannot_close_the_script_element_that_holds_it(self) -> None:
        assert '</script' not in read_asset('page.js').lower()

    def test_the_map_header_styles_every_class_a_map_node_can_take(self) -> None:
        header = read_case_asset('map.mmd')

        classes = {name for name in (*ENTRY_KINDS, 'retired') if f'classDef k_{name} ' in header}
        assert classes == {*ENTRY_KINDS, 'retired'}

    def test_the_map_header_opens_a_top_down_flowchart(self) -> None:
        assert read_case_asset('map.mmd').startswith('flowchart TD\n')
