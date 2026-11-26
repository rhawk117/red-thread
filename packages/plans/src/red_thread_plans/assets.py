"""The plan's own assets: the header of the worktree chart."""

from typing import Literal

from red_thread_core.assets import read_package_asset

type AssetName = Literal['worktrees.mmd']


def read_asset(name: AssetName) -> str:
    return read_package_asset(__file__, name)
