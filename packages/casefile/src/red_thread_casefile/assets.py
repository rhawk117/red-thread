"""The case file's own assets: the map header, and the worktree header of the plan page."""

from typing import Literal

from red_thread_core.assets import read_package_asset

type AssetName = Literal['map.mmd', 'lanes.mmd']


def read_asset(name: AssetName) -> str:
    return read_package_asset(__file__, name)
