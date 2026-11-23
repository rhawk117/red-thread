"""The refusals the slice verb makes: plain exceptions holding an already-fitted message."""

from typing import TYPE_CHECKING

from red_thread_navigate.address import AddressError

if TYPE_CHECKING:
    from pathlib import PurePosixPath


class SliceError(ValueError):
    pass


class FileRefusedError(SliceError):
    def __init__(self, *, path: PurePosixPath, reason: str, message: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(message)


class UnknownSymbolError(SliceError):
    def __init__(self, *, name: str, nearest: tuple[str, ...], message: str) -> None:
        self.name = name
        self.nearest = nearest
        super().__init__(message)


class LinesOutOfRangeError(SliceError):
    def __init__(self, *, start: int, total: int, message: str) -> None:
        self.start = start
        self.total = total
        super().__init__(message)


class HintedOutsideRootError(AddressError):
    def __init__(self, *, text: str, root: str, message: str) -> None:
        self.text = text
        self.root = root
        super().__init__(message)
