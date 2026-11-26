"""The files the case file package ships: the map header, the board's wording and the lenses."""

from typing import Literal

from red_thread_core.packaged import load_asset, read_asset_text

from red_thread_casefile.documents import Wording
from red_thread_casefile.lenses import LensBook

type AssetName = Literal['map.mmd']

CASEFILE_PACKAGE = 'red_thread_casefile'
WORDING_FILE = 'wording.yaml'
LENSES_FILE = 'lenses.yaml'


def read_asset(name: AssetName) -> str:
    return read_asset_text(CASEFILE_PACKAGE, name)


def load_wording() -> Wording:
    return load_asset(CASEFILE_PACKAGE, WORDING_FILE, Wording)


def load_lens_book() -> LensBook:
    return load_asset(CASEFILE_PACKAGE, LENSES_FILE, LensBook)
