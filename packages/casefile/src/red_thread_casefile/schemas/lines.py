"""The case file's numbering: a file's first line, and an entry or round head with its number."""

from red_thread_core.dto import DTO
from red_thread_core.lines import Line

FIRST_LINE = 1


class Numbered(DTO, frozen=True, kw_only=True, gc=False):
    line: Line
    seq: int
