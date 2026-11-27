from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

from red_thread_core.dto import DTO

if TYPE_CHECKING:
    from red_thread_navigate.walk import SourceFile

type SymbolKind = Literal[
    'class',
    'function',
    'method',
    'property',
    'interface',
    'type',
    'enum',
    'struct',
    'trait',
    'constant',
    'variable',
    'module',
    'resource',
    'data',
    'output',
    'local',
]


class Symbol(DTO, frozen=True, kw_only=True, gc=False):
    name: str
    qualified_name: str
    kind: SymbolKind
    start_line: int
    end_line: int
    signature: str
    docstring: str | None
    parent: str | None
    impl: str | None = None

    @property
    def kind_label(self) -> str:
        if self.impl is None:
            return self.kind
        return f'{self.kind} (impl {self.impl})'


class Reference(DTO, frozen=True, kw_only=True, gc=False):
    name: str
    line: int


class FileSymbols(DTO, frozen=True, kw_only=True, gc=False):
    path: PurePosixPath
    language: str
    symbols: tuple[Symbol, ...]
    references: tuple[Reference, ...]
    notes: tuple[str, ...]


@runtime_checkable
class Backend(Protocol):
    @property
    def language(self) -> str: ...

    @property
    def suffixes(self) -> frozenset[str]: ...

    def parse(self, source: SourceFile) -> FileSymbols: ...


@runtime_checkable
class Backends(Protocol):
    def for_path(self, path: PurePosixPath) -> Backend | None: ...

    def available(self) -> tuple[Backend, ...]: ...
