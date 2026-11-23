"""Text-cutting helpers: shorten paths and names and fit a refusal to a token budget."""

import re
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from red_thread_navigate.budget import ELLIPSIS

if TYPE_CHECKING:
    from collections.abc import Iterator

MIN_SHOWN = 8
FILE_NAME_FLOOR = 20
PLACEHOLDER = re.compile(r'<path>|<name>')


def shorten_path(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f'{ELLIPSIS}{text[len(ELLIPSIS) - limit :]}'


def shorten_name(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return f'{text[: limit - len(ELLIPSIS)]}{ELLIPSIS}'


def fill(template: str, *, path: str, name: str) -> str:
    shown = {'<path>': path, '<name>': name}
    segments = PLACEHOLDER.split(template)
    values = [shown[token] for token in PLACEHOLDER.findall(template)]
    return ''.join(
        f'{segment}{value}' for segment, value in zip(segments, [*values, ''], strict=True)
    )


def cut_floor(full_path: str) -> int:
    file_name = PurePosixPath(full_path).name
    return min(len(full_path), max(MIN_SHOWN, min(len(file_name), FILE_NAME_FLOOR) + len(ELLIPSIS)))


def cut_steps(full_path: str, name: str) -> Iterator[tuple[int, int]]:
    floor = cut_floor(full_path)
    name_floor = min(len(name), MIN_SHOWN)
    yield from ((limit, len(name)) for limit in range(len(full_path), floor - 1, -1))
    yield from ((floor, limit) for limit in range(len(name), name_floor - 1, -1))


def deep_cut_steps(full_path: str, name: str) -> Iterator[tuple[int, int]]:
    yield from cut_steps(full_path, name)
    floor = cut_floor(full_path)
    name_floor = min(len(name), MIN_SHOWN)
    yield from ((limit, name_floor) for limit in range(floor, MIN_SHOWN - 1, -1))
