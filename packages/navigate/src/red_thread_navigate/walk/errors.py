"""Refusals the walk raises before it lists anything."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class PathMissingError(ValueError):
    """The path a verb was asked to read does not exist."""

    def __init__(self, *, path: Path) -> None:
        self.path = path
        super().__init__(f'{path} does not exist')
