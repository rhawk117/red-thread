"""Refusals the walk raises before it lists anything."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class PathMissingError(ValueError):
    def __init__(self, *, path: Path) -> None:
        self.path = path
        super().__init__(f'{path} does not exist')
