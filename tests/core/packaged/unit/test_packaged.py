"""Packaged assets: every name the page needs reads from the package, and a missing one fails."""

from typing import get_args

import pytest
from red_thread_core.packaged import CORE_PACKAGE, CoreAsset, read_asset, read_asset_text


def core_asset_cases() -> pytest.MarkDecorator:
    names = get_args(CoreAsset.__value__)
    return pytest.mark.parametrize('name', [pytest.param(name, id=name) for name in names])


class TestReadAsset:
    @core_asset_cases()
    def test_each_core_asset_reads_as_text_from_the_package(self, name: CoreAsset) -> None:
        assert read_asset(name).strip()

    def test_a_name_with_a_directory_reads_from_below_the_assets(self) -> None:
        assert read_asset_text('red_thread_navigate', 'queries/go.scm').strip()

    def test_a_missing_asset_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            read_asset_text(CORE_PACKAGE, 'missing.yaml')
