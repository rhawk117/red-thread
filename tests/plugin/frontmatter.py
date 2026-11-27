"""Reads the YAML frontmatter of an agent or skill file, one line at a time."""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def read_frontmatter_lines(file: Path) -> tuple[str, ...]:
    lines = file.read_text(encoding='utf-8').splitlines()
    assert lines[0] == '---'
    closing = lines.index('---', 1)
    return tuple(lines[1:closing])


def read_scalar(lines: Sequence[str], key: str) -> str | None:
    values = [line.partition(':')[2].strip() for line in lines if line.startswith(f'{key}:')]
    return next(iter(values), None)


def read_flow_list(lines: Sequence[str], key: str) -> tuple[str, ...]:
    value = read_scalar(lines, key) or ''
    items = re.fullmatch(r'\[(.*)\]', value)
    if not items:
        return ()

    return tuple(item.strip() for item in items.group(1).split(',') if item.strip())
