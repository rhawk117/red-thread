"""Language backends and the lookup that picks one by file suffix."""

from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING

import tree_sitter
import tree_sitter_go
import tree_sitter_hcl
import tree_sitter_javascript
import tree_sitter_rust
import tree_sitter_typescript

from red_thread_navigate.symbols.store.python import PythonBackend
from red_thread_navigate.symbols.store.treesitter import TreeSitterSpec, create_tree_sitter_backend

if TYPE_CHECKING:
    from pathlib import PurePosixPath

    from red_thread_navigate.symbols.domain import Backend


@cache
def create_backends() -> tuple[Backend, ...]:
    specs = (
        TreeSitterSpec(
            language='javascript',
            suffixes=frozenset({'.js', '.mjs', '.cjs', '.jsx'}),
            grammar=tree_sitter.Language(tree_sitter_javascript.language()),
        ),
        TreeSitterSpec(
            language='typescript',
            suffixes=frozenset({'.ts', '.mts', '.cts'}),
            grammar=tree_sitter.Language(tree_sitter_typescript.language_typescript()),
        ),
        TreeSitterSpec(
            language='tsx',
            suffixes=frozenset({'.tsx'}),
            grammar=tree_sitter.Language(tree_sitter_typescript.language_tsx()),
            query_name='typescript',
        ),
        TreeSitterSpec(
            language='go',
            suffixes=frozenset({'.go'}),
            grammar=tree_sitter.Language(tree_sitter_go.language()),
        ),
        TreeSitterSpec(
            language='terraform',
            suffixes=frozenset({'.tf'}),
            grammar=tree_sitter.Language(tree_sitter_hcl.language()),
            aliases={'variable': 'var', 'locals': 'local'},
        ),
        TreeSitterSpec(
            language='rust',
            suffixes=frozenset({'.rs'}),
            grammar=tree_sitter.Language(tree_sitter_rust.language()),
        ),
    )
    return (PythonBackend(), *map(create_tree_sitter_backend, specs))


def backend_for(path: PurePosixPath) -> Backend | None:
    return next((backend for backend in create_backends() if path.suffix in backend.suffixes), None)


@dataclass(slots=True, kw_only=True, frozen=True)
class RegistryBackends:
    def for_path(self, path: PurePosixPath) -> Backend | None:
        return backend_for(path)

    def available(self) -> tuple[Backend, ...]:
        return create_backends()


__all__ = ['RegistryBackends', 'backend_for', 'create_backends']
