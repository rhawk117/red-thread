"""The one base every red-thread package's failures derive from, so a CLI can catch them all."""

from typing import Literal

type Format = Literal['json', 'yaml']


class RedThreadError(Exception):
    pass


class MalformedDocumentError(RedThreadError):
    def __init__(self, *, form: Format, reason: str) -> None:
        self.form = form
        self.reason = reason
        super().__init__(reason)
