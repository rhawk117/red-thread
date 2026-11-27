import time
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, get_args

import tree_sitter
from red_thread_core.packaged import read_asset_text

from red_thread_navigate.symbols.domain import FileSymbols, Reference, Symbol, SymbolKind
from red_thread_navigate.util import split_lines

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import PurePosixPath

    from red_thread_navigate.walk import SourceFile

NAVIGATE_PACKAGE = 'red_thread_navigate'
DEFINITION_PREFIX = 'definition.'
REFERENCE_PREFIX = 'reference.'
READ_CHUNK_BYTES = 65536
UNCAPTURED_KINDS: frozenset[SymbolKind] = frozenset({'property'})
KINDS: Mapping[str, SymbolKind] = MappingProxyType({
    kind: kind for kind in get_args(SymbolKind.__value__) if kind not in UNCAPTURED_KINDS
})


@dataclass(slots=True, kw_only=True, frozen=True)
class Definition:
    name: str
    kind: SymbolKind
    node: tree_sitter.Node
    parent: str | None = None
    impl: str | None = None


def load_query_source(query_name: str) -> str:
    return read_asset_text(NAVIGATE_PACKAGE, f'queries/{query_name}.scm')


@dataclass(slots=True, kw_only=True, frozen=True)
class SourceReader:
    data: bytes

    def read(self, offset: int, _point: tree_sitter.Point) -> bytes:
        return self.data[offset : offset + READ_CHUNK_BYTES]


@dataclass(slots=True, kw_only=True, frozen=True)
class Deadline:
    expires_at: float

    def is_expired(self, *_progress: object) -> bool:
        return time.monotonic() >= self.expires_at


def first_text_of(captures: dict[str, list[tree_sitter.Node]], key: str) -> str | None:
    nodes = captures.get(key, [])
    if not nodes:
        return None
    return text_of(nodes[0])


def capture_prefix_of(captures: dict[str, list[tree_sitter.Node]], prefix: str) -> str | None:
    return next((name for name in captures if name.startswith(prefix)), None)


def text_of(node: tree_sitter.Node) -> str:
    return (node.text or b'').decode('utf-8', errors='replace')


def contains(outer: tree_sitter.Node, inner: tree_sitter.Node) -> bool:
    return outer.start_byte <= inner.start_byte and inner.end_byte <= outer.end_byte


def address_of(captures: dict[str, list[tree_sitter.Node]], aliases: Mapping[str, str]) -> str:
    head = text_of(captures['name'][0])
    parts = [aliases.get(head, head), *(text_of(tail) for tail in captures.get('tail', []))]
    return '.'.join(parts)


def first_error_line(root: tree_sitter.Node) -> int | None:
    if not root.has_error:
        return None

    rows: list[int] = []
    pending = [root]
    while pending:
        node = pending.pop()
        if node.is_error or node.is_missing:
            rows.append(node.start_point.row + 1)
        pending.extend(child for child in node.children if child.has_error or child.is_missing)
    return min(rows, default=None)


def note_only(path: PurePosixPath, language: str, note: str) -> FileSymbols:
    return FileSymbols(path=path, language=language, symbols=(), references=(), notes=(note,))


def collect_definitions(
    matches: list[tuple[int, dict[str, list[tree_sitter.Node]]]], aliases: Mapping[str, str]
) -> list[Definition]:
    found: dict[tuple[int, int], Definition] = {}
    for _index, captures in matches:
        capture = capture_prefix_of(captures, DEFINITION_PREFIX)
        if capture is None or 'name' not in captures:
            continue

        node = captures[capture][0]
        kind = KINDS[capture.removeprefix(DEFINITION_PREFIX)]
        definition = Definition(
            name=address_of(captures, aliases),
            kind=kind,
            node=node,
            parent=first_text_of(captures, 'parent'),
            impl=first_text_of(captures, 'impl'),
        )
        found.setdefault((node.start_byte, node.end_byte), definition)
    return sorted(found.values(), key=by_position)


def by_position(definition: Definition) -> tuple[int, int]:
    return (definition.node.start_byte, -definition.node.end_byte)


def build_symbols(definitions: list[Definition], lines: tuple[str, ...]) -> list[Symbol]:
    symbols: list[Symbol] = []
    open_scopes: list[Definition] = []
    names: list[str] = []
    for definition in definitions:
        while open_scopes and not contains(open_scopes[-1].node, definition.node):
            open_scopes.pop()
            names.pop()

        parent = definition.parent or (names[-1] if names else None)
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
                impl=definition.impl,
            )
        )
        open_scopes.append(definition)
        names.append(qualified_name)
    return symbols


def collect_references(
    matches: list[tuple[int, dict[str, list[tree_sitter.Node]]]], aliases: Mapping[str, str]
) -> tuple[Reference, ...]:
    found: set[tuple[int, str]] = set()
    for _index, captures in matches:
        if capture_prefix_of(captures, REFERENCE_PREFIX) is None or 'name' not in captures:
            continue

        name_node = captures['name'][0]
        found.add((name_node.end_point.row + 1, address_of(captures, aliases)))
    return tuple(Reference(name=name, line=line) for line, name in sorted(found))


@dataclass(slots=True, kw_only=True, frozen=True)
class TreeSitterBackend:
    language: str
    suffixes: frozenset[str]
    grammar: tree_sitter.Language
    query: tree_sitter.Query
    deadline_seconds: float = 2.0
    aliases: Mapping[str, str] = field(default_factory=dict)

    def get_failure_note(self, source: SourceFile, deadline: Deadline, reason: str) -> str:
        if deadline.is_expired():
            return f'{source.path}: parse stopped after the {self.deadline_seconds} s time limit'
        return f'{source.path}: parse failed: {reason}'

    def parse_tree(self, source: SourceFile) -> tree_sitter.Tree | FileSymbols:
        reader = SourceReader(data=source.text.encode('utf-8'))
        parser = tree_sitter.Parser(self.grammar)
        deadline = Deadline(expires_at=time.monotonic() + self.deadline_seconds)
        try:
            tree = parser.parse(reader.read, progress_callback=deadline.is_expired)
        except ValueError as error:
            note = self.get_failure_note(source, deadline, str(error))
            return note_only(source.path, self.language, note)

        if tree is None:
            note = self.get_failure_note(source, deadline, 'the parser returned no tree')
            return note_only(source.path, self.language, note)
        return tree

    def build_file_symbols(self, source: SourceFile, tree: tree_sitter.Tree) -> FileSymbols:
        error_line = first_error_line(tree.root_node)
        notes = () if error_line is None else (f'{source.path}: syntax error at line {error_line}',)
        matches = tree_sitter.QueryCursor(self.query).matches(tree.root_node)
        definitions = collect_definitions(matches, self.aliases)
        return FileSymbols(
            path=source.path,
            language=self.language,
            symbols=tuple(build_symbols(definitions, split_lines(source.text))),
            references=collect_references(matches, self.aliases),
            notes=notes,
        )

    def parse(self, source: SourceFile) -> FileSymbols:
        parsed = self.parse_tree(source)
        if isinstance(parsed, FileSymbols):
            return parsed
        return self.build_file_symbols(source, parsed)


@dataclass(slots=True, kw_only=True, frozen=True)
class TreeSitterSpec:
    language: str
    suffixes: frozenset[str]
    grammar: tree_sitter.Language
    query_name: str | None = None
    aliases: Mapping[str, str] = field(default_factory=dict)

    @property
    def query_stem(self) -> str:
        return self.query_name or self.language


def create_tree_sitter_backend(spec: TreeSitterSpec) -> TreeSitterBackend:
    query = tree_sitter.Query(spec.grammar, load_query_source(spec.query_stem))
    return TreeSitterBackend(
        language=spec.language,
        suffixes=spec.suffixes,
        grammar=spec.grammar,
        query=query,
        aliases=MappingProxyType(dict(spec.aliases)),
    )
