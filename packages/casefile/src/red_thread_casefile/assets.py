"""The case file's own asset: the header of the case map."""

from typing import Literal

from red_thread_core.assets import read_package_asset

type AssetName = Literal['map.mmd']


def read_asset(name: AssetName) -> str:
    return read_package_asset(__file__, name)
