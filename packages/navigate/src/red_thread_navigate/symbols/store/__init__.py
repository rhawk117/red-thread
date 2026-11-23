"""Language backends and the lookup that picks one by file suffix."""

from typing import TYPE_CHECKING

from red_thread_navigate.symbols.store.python import PYTHON_BACKEND
from red_thread_navigate.symbols.store.treesitter import (
    GO_BACKEND,
    JAVASCRIPT_BACKEND,
    TERRAFORM_BACKEND,
    TSX_BACKEND,
    TYPESCRIPT_BACKEND,
)

if TYPE_CHECKING:
    from pathlib import PurePosixPath

    from red_thread_navigate.symbols.domain import Backend

BACKENDS: tuple[Backend, ...] = (
    PYTHON_BACKEND,
    JAVASCRIPT_BACKEND,
    TYPESCRIPT_BACKEND,
    TSX_BACKEND,
    GO_BACKEND,
    TERRAFORM_BACKEND,
)


def backend_for(path: PurePosixPath) -> Backend | None:
    for backend in BACKENDS:
        if path.suffix in backend.suffixes:
            return backend
    return None


__all__ = [
    'BACKENDS',
    'GO_BACKEND',
    'JAVASCRIPT_BACKEND',
    'PYTHON_BACKEND',
    'TERRAFORM_BACKEND',
    'TSX_BACKEND',
    'TYPESCRIPT_BACKEND',
    'backend_for',
]
