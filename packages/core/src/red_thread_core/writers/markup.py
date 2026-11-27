"""The Jinja environment pages are drawn with: each package's templates, every value escaped."""

import re
from typing import TYPE_CHECKING

from jinja2 import ChoiceLoader, Environment, PackageLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

from red_thread_core.packaged import ASSETS, CORE_PACKAGE

if TYPE_CHECKING:
    from collections.abc import Mapping

NOT_ANCHOR = re.compile(r'[^a-z0-9]+')
TEMPLATE_SUFFIXES = ('html.j2',)
SAFE_SCHEMES = frozenset({'', 'http', 'https'})
URL_SCHEME = re.compile(r'[a-z][a-z0-9+.-]*(?=:)', re.IGNORECASE)
URL_NOISE = re.compile(r'[\t\n\r]')
C0_AND_SPACE = ''.join(map(chr, range(0x21)))


def anchor_section(title: str) -> str:
    return 'section-' + NOT_ANCHOR.sub('-', title.lower()).strip('-')


def find_scheme(url: str) -> str:
    found = URL_SCHEME.match(URL_NOISE.sub('', url).lstrip(C0_AND_SPACE))
    return found.group().lower() if found else ''


def keep_safe_url(url: str) -> str:
    return url if find_scheme(url) in SAFE_SCHEMES else ''


def write_attribute(name: str, value: object) -> Markup:
    if value is True:
        return Markup(' {}').format(name)
    return Markup(' {}="{}"').format(name, value)


def is_written(value: object) -> bool:
    return value is not None and value is not False


def write_attributes(attributes: Mapping[str, object]) -> Markup:
    kept = (write_attribute(name, value) for name, value in attributes.items() if is_written(value))
    return Markup('').join(kept)


def create_page_environment(*packages: str) -> Environment:
    loaders = [PackageLoader(package, ASSETS) for package in (*packages, CORE_PACKAGE)]
    environment = Environment(
        loader=ChoiceLoader(loaders),
        autoescape=select_autoescape(TEMPLATE_SUFFIXES),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    environment.filters.update(
        anchor=anchor_section, safe_url=keep_safe_url, attributes=write_attributes
    )
    return environment
