"""The case file's numbering: a file's first line, and an entry or round head with its number."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from red_thread_core.lines import Line

FIRST_LINE = 1


@dataclass(slots=True, kw_only=True, frozen=True)
class Numbered:
    line: Line
    seq: int
