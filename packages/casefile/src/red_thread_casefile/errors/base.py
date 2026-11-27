"""The root of every failure the case file reports, and how a failure names its place."""

from typing import TYPE_CHECKING

from red_thread_core.errors import RedThreadError

if TYPE_CHECKING:
    from red_thread_casefile.domain import FindingLocation


class CaseFileError(RedThreadError):
    pass


def name_place(location: FindingLocation) -> str:
    return f'{location.label}:'
