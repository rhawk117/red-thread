"""The page assets by name, read from the Literal the asset reader takes."""

from typing import get_args

from red_thread_casefile.assets import AssetName

ASSET_NAMES: tuple[AssetName, ...] = get_args(AssetName.__value__)
