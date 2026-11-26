"""The files a package ships in its own assets directory, read as text or decoded from YAML."""

from importlib import resources
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Literal

import msgspec

if TYPE_CHECKING:
    from importlib.resources.abc import Traversable

type CoreAsset = Literal['page.html', 'page.css', 'tailwind.css', 'page.js']

ASSETS = 'assets'
CORE_PACKAGE = 'red_thread_core'


def find_asset(package: str, name: str) -> Traversable:
    return resources.files(package).joinpath(ASSETS, *PurePosixPath(name).parts)


def read_asset_text(package: str, name: str) -> str:
    return find_asset(package, name).read_text(encoding='utf-8')


def load_asset[T](package: str, name: str, shape: type[T]) -> T:
    return msgspec.yaml.decode(find_asset(package, name).read_bytes(), type=shape)


def read_asset(name: CoreAsset) -> str:
    return read_asset_text(CORE_PACKAGE, name)
