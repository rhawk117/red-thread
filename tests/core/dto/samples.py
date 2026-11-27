"""A small record built on DTO, standing in for the package records in the DTO tests."""

from red_thread_core.dto import DTO


class Sample(DTO, frozen=True, kw_only=True, forbid_unknown_fields=True, gc=False):
    name: str
    count: int = 0
    tags: tuple[str, ...] = ()
