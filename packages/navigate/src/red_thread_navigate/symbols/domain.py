from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

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


class Backend(Protocol):
    @property
    def language(self) -> str: ...

    @property
    def suffixes(self) -> frozenset[str]: ...

    def parse(self, source: SourceFile) -> FileSymbols: ...
