"""Parsing a slice address into a file and a target, and keeping it inside the root."""

import posixpath
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from red_thread_navigate.address.errors import (
    MalformedAddressError,
    OutsideRootError,
)

if TYPE_CHECKING:
    from pathlib import Path


LINE_PATTERN = re.compile(r'L(\d+)(?:-L(\d+))?')


@dataclass(slots=True, kw_only=True, frozen=True)
class SymbolTarget:
    parts: tuple[str, ...]


@dataclass(slots=True, kw_only=True, frozen=True)
class LineTarget:
    start: int
    end: int


type Target = SymbolTarget | LineTarget


@dataclass(slots=True, kw_only=True, frozen=True)
class Address:
    path: PurePosixPath
    target: Target


def parse_symbol(text: str, fragment: str) -> SymbolTarget:
    parts = tuple(fragment.split('.'))
    if not all(parts):
        raise MalformedAddressError(text=text, reason='a symbol has an empty dotted segment')

    if any(part != part.strip() or ' ' in part for part in parts):
        raise MalformedAddressError(text=text, reason='a symbol contains whitespace')

    return SymbolTarget(parts=parts)


def parse_lines(text: str, match: re.Match[str]) -> LineTarget:
    first, last = match.groups()
    start = int(first)
    end = int(last or first)
    if start < 1:
        raise MalformedAddressError(text=text, reason='lines start at L1')

    if end < start:
        raise MalformedAddressError(text=text, reason='a line range ends before it starts')

    return LineTarget(start=start, end=end)


def parse_target(text: str, fragment: str) -> Target:
    if not fragment:
        raise MalformedAddressError(text=text, reason='the symbol or lines after # are empty')

    if match := LINE_PATTERN.fullmatch(fragment):
        return parse_lines(text, match)

    return parse_symbol(text, fragment)


def contain_path(text: str, file: str, root: Path) -> PurePosixPath:
    root_text = posixpath.normpath(root.as_posix())
    joined = posixpath.normpath(posixpath.join(root_text, file))
    try:
        relative = PurePosixPath(joined).relative_to(root_text)
    except ValueError:
        raise OutsideRootError(text=text, root=root_text) from None

    if '..' in relative.parts:
        raise OutsideRootError(text=text, root=root_text)

    if not relative.parts:
        raise MalformedAddressError(text=text, reason='the file names the root, not a file')

    return relative


def parse_address(text: str, *, root: Path) -> Address:
    file, separator, fragment = text.rpartition('#')
    if not separator:
        raise MalformedAddressError(text=text, reason='there is no # between file and target')

    if not file:
        raise MalformedAddressError(text=text, reason='the file before # is empty')

    target = parse_target(text, fragment)
    return Address(path=contain_path(text, file, root), target=target)
