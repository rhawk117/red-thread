"""The page assets by name, typed as the reader takes them."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from red_thread_casefile.assets import AssetName

ASSET_NAMES: tuple[AssetName, ...] = ('page.html', 'page.css', 'tailwind.css', 'page.js', 'map.mmd')
