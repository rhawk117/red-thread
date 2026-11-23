"""Language backends and the lookup that picks one by file suffix."""

from typing import TYPE_CHECKING

from red_thread_navigate.symbols.store.python import PYTHON_BACKEND

if TYPE_CHECKING:
    from pathlib import PurePosixPath

    from red_thread_navigate.symbols.domain import Backend

BACKENDS: tuple[Backend, ...] = (PYTHON_BACKEND,)


def backend_for(path: PurePosixPath) -> Backend | None:
    for backend in BACKENDS:
        if path.suffix in backend.suffixes:
            return backend
    return None


__all__ = ['BACKENDS', 'PYTHON_BACKEND', 'backend_for']
