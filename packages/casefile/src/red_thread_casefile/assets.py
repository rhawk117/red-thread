"""The assets beside the package source: the page skeleton, styles, script and map headers."""

from pathlib import Path
from typing import Literal

type AssetName = Literal['page.html', 'page.css', 'tailwind.css', 'page.js', 'map.mmd', 'lanes.mmd']

LEVELS_ABOVE = 2


def read_asset(name: AssetName) -> str:
    package = Path(__file__).resolve().parents[LEVELS_ABOVE]
    return package.joinpath('assets', name).read_text(encoding='utf-8')
