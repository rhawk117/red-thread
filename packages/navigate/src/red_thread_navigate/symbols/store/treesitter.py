import time
from dataclasses import dataclass
from importlib import resources
from typing import TYPE_CHECKING

import tree_sitter
import tree_sitter_javascript

from red_thread_navigate.symbols.domain import FileSymbols, Reference, Symbol

if TYPE_CHECKING:
    from collections.abc import Callable

    from red_thread_navigate.symbols.domain import SymbolKind
    from red_thread_navigate.walk import SourceFile

DEFINITION_PREFIX = 'definition.'
REFERENCE_PREFIX = 'reference.'
READ_CHUNK_BYTES = 65536

KINDS: dict[str, SymbolKind] = {
    'class': 'class',
    'function': 'function',
    'method': 'method',
    'interface': 'interface',
    'type': 'type',
    'enum': 'enum',
    'struct': 'struct',
    'trait': 'trait',
    'constant': 'constant',
    'module': 'module',
}


@dataclass(slots=True, kw_only=True, frozen=True)
class Definition:
    name: str
    kind: SymbolKind
    node: tree_sitter.Node


def load_query_source(query_name: str) -> str:
    query_file = resources.files('red_thread_navigate.symbols.store').joinpath(
        'queries', f'{query_name}.scm'
    )
    return query_file.read_text(encoding='utf-8')


def create_reader(data: bytes) -> Callable[[int, tree_sitter.Point], bytes]:
    def read(offset: int, _point: tree_sitter.Point) -> bytes:
        return data[offset : offset + READ_CHUNK_BYTES]

    return read


def create_deadline(seconds: float) -> Callable[[int, bool], bool]:
    expires_at = time.monotonic() + seconds

    def expired(*_progress: object) -> bool:
        return time.monotonic() >= expires_at

    return expired


def capture_prefix_of(captures: dict[str, list[tree_sitter.Node]], prefix: str) -> str | None:
    return next((name for name in captures if name.startswith(prefix)), None)


def text_of(node: tree_sitter.Node) -> str:
    return (node.text or b'').decode('utf-8', errors='replace')


def contains(outer: tree_sitter.Node, inner: tree_sitter.Node) -> bool:
    return outer.start_byte <= inner.start_byte and inner.end_byte <= outer.end_byte


def collect_definitions(
    matches: list[tuple[int, dict[str, list[tree_sitter.Node]]]],
) -> list[Definition]:
    found: dict[tuple[int, int], Definition] = {}
    for _index, captures in matches:
        capture = capture_prefix_of(captures, DEFINITION_PREFIX)
        if capture is None or 'name' not in captures:
            continue

        node = captures[capture][0]
        kind = KINDS[capture.removeprefix(DEFINITION_PREFIX)]
        definition = Definition(name=text_of(captures['name'][0]), kind=kind, node=node)
        found.setdefault((node.start_byte, node.end_byte), definition)
    return sorted(found.values(), key=lambda item: (item.node.start_byte, -item.node.end_byte))


def build_symbols(definitions: list[Definition], lines: list[str]) -> list[Symbol]:
    symbols: list[Symbol] = []
    open_scopes: list[Definition] = []
    names: list[str] = []
    for definition in definitions:
        while open_scopes and not contains(open_scopes[-1].node, definition.node):
            open_scopes.pop()
            names.pop()

        parent = names[-1] if names else None
        qualified_name = definition.name if parent is None else f'{parent}.{definition.name}'
        start_line = definition.node.start_point.row + 1
        symbols.append(
            Symbol(
                name=definition.name,
                qualified_name=qualified_name,
                kind=definition.kind,
                start_line=start_line,
                end_line=definition.node.end_point.row + 1,
                signature=lines[start_line - 1].strip(),
                docstring=None,
                parent=parent,
            )
        )
        open_scopes.append(definition)
        names.append(qualified_name)
    return symbols


def collect_references(
    matches: list[tuple[int, dict[str, list[tree_sitter.Node]]]],
) -> tuple[Reference, ...]:
    found: set[tuple[int, str]] = set()
    for _index, captures in matches:
        if capture_prefix_of(captures, REFERENCE_PREFIX) is None or 'name' not in captures:
            continue

        name_node = captures['name'][0]
        found.add((name_node.end_point.row + 1, text_of(name_node)))
    return tuple(Reference(name=name, line=line) for line, name in sorted(found))


@dataclass(slots=True, kw_only=True, frozen=True)
class TreeSitterBackend:
    language: str
    suffixes: frozenset[str]
    grammar: tree_sitter.Language
    query_name: str
    deadline_seconds: float = 2.0

    def parse(self, source: SourceFile) -> FileSymbols:
        data = source.text.encode('utf-8')
        parser = tree_sitter.Parser(self.grammar)
        try:
            tree = parser.parse(
                create_reader(data), progress_callback=create_deadline(self.deadline_seconds)
            )
        except ValueError:
            tree = None
        if tree is None:
            note = f'{source.path}: parse stopped after the {self.deadline_seconds} s time limit'
            return FileSymbols(
                path=source.path, language=self.language, symbols=(), references=(), notes=(note,)
            )

        query = tree_sitter.Query(self.grammar, load_query_source(self.query_name))
        matches = tree_sitter.QueryCursor(query).matches(tree.root_node)
        definitions = collect_definitions(matches)
        return FileSymbols(
            path=source.path,
            language=self.language,
            symbols=tuple(build_symbols(definitions, source.text.splitlines())),
            references=collect_references(matches),
            notes=(),
        )


JAVASCRIPT_BACKEND = TreeSitterBackend(
    language='javascript',
    suffixes=frozenset({'.js', '.mjs', '.cjs', '.jsx'}),
    grammar=tree_sitter.Language(tree_sitter_javascript.language()),
    query_name='javascript',
)
