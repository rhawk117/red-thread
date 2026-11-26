"""The page assets by name, read from the Literal the asset reader takes."""

from typing import get_args

from red_thread_core.packaged import CoreAsset

ASSET_NAMES: tuple[CoreAsset, ...] = get_args(CoreAsset.__value__)
