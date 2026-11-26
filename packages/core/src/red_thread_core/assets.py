"""Reads a file from a package's assets directory, beside its source."""

from pathlib import Path
from typing import Literal

type CoreAsset = Literal['page.html', 'page.css', 'tailwind.css', 'page.js']

LEVELS_ABOVE = 2


def read_package_asset(anchor: str, name: str) -> str:
    package = Path(anchor).resolve().parents[LEVELS_ABOVE]
    return package.joinpath('assets', name).read_text(encoding='utf-8')


def read_asset(name: CoreAsset) -> str:
    return read_package_asset(__file__, name)
