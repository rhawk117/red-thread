"""The files a package ships in its own assets directory, read as text or decoded from YAML."""

from importlib import resources
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Literal

from red_thread_core.codec import create_yaml_codec
from red_thread_core.errors import MalformedDocumentError

if TYPE_CHECKING:
    from importlib.resources.abc import Traversable

type CoreAsset = Literal['page.css', 'tailwind.css', 'page.js']

ASSETS = 'assets'
TEMPLATES = 'templates'
CORE_PACKAGE = 'red_thread_core'


def find_asset(package: str, name: str) -> Traversable:
    return resources.files(package).joinpath(ASSETS, *PurePosixPath(name).parts)


def read_asset_text(package: str, name: str) -> str:
    return find_asset(package, name).read_text(encoding='utf-8')


def load_asset[T](package: str, name: str, shape: type[T]) -> T:
    decoded = create_yaml_codec().decode(find_asset(package, name).read_bytes(), shape)
    if isinstance(decoded, MalformedDocumentError):
        raise decoded

    return decoded


def read_asset(name: CoreAsset) -> str:
    return read_asset_text(CORE_PACKAGE, name)
