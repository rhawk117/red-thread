"""The root of every failure the case file reports, and how a failure names its place."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from red_thread_casefile.domain import Spot


class CaseFileError(Exception):
    pass


def name_place(spot: Spot) -> str:
    return f'{spot.label}:'
