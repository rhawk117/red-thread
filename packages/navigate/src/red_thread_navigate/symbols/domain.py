from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import PurePosixPath

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


@dataclass(slots=True, kw_only=True, frozen=True)
class Symbol:
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


@dataclass(slots=True, kw_only=True, frozen=True)
class Reference:
    name: str
    line: int


@dataclass(slots=True, kw_only=True, frozen=True)
class FileSymbols:
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
