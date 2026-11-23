import re
import time
from dataclasses import dataclass, field
from importlib import resources
from typing import TYPE_CHECKING

import tree_sitter
import tree_sitter_go
import tree_sitter_hcl
import tree_sitter_javascript
import tree_sitter_rust
import tree_sitter_typescript

from red_thread_navigate.symbols.domain import FileSymbols, Reference, Symbol

if TYPE_CHECKING:
    from collections.abc import Callable

    from red_thread_navigate.symbols.domain import SymbolKind
    from red_thread_navigate.walk import SourceFile

DEFINITION_PREFIX = 'definition.'
REFERENCE_PREFIX = 'reference.'
READ_CHUNK_BYTES = 65536
LINE_BREAK = re.compile(r'\r\n|\r|\n')

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
    'variable': 'variable',
    'resource': 'resource',
    'data': 'data',
    'output': 'output',
    'local': 'local',
}


@dataclass(slots=True, kw_only=True, frozen=True)
class Definition:
    name: str
    kind: SymbolKind
    node: tree_sitter.Node
    parent: str | None = None
    impl: str | None = None


def load_query_source(query_name: str) -> str:
    query_file = resources.files('red_thread_navigate.symbols.store').joinpath(
        'queries', f'{query_name}.scm'
    )
    return query_file.read_text(encoding='utf-8')


def create_reader(data: bytes) -> Callable[[int, tree_sitter.Point], bytes]:
    def read(offset: int, _point: tree_sitter.Point) -> bytes:
        return data[offset : offset + READ_CHUNK_BYTES]

    return read


@dataclass(slots=True)
class Deadline:
    expires_at: float
    fired: bool = False

    def __call__(self, *_progress: object) -> bool:
        if time.monotonic() >= self.expires_at:
            self.fired = True
        return self.fired


def capture_prefix_of(captures: dict[str, list[tree_sitter.Node]], prefix: str) -> str | None:
    return next((name for name in captures if name.startswith(prefix)), None)


def text_of(node: tree_sitter.Node) -> str:
    return (node.text or b'').decode('utf-8', errors='replace')


def contains(outer: tree_sitter.Node, inner: tree_sitter.Node) -> bool:
    return outer.start_byte <= inner.start_byte and inner.end_byte <= outer.end_byte


def address_of(captures: dict[str, list[tree_sitter.Node]], aliases: dict[str, str]) -> str:
    head = text_of(captures['name'][0])
    parts = [aliases.get(head, head), *(text_of(tail) for tail in captures.get('tail', []))]
    return '.'.join(parts)


def first_error_line(root: tree_sitter.Node) -> int | None:
    pending = [root]
    while pending:
        node = pending.pop()
        if node.is_error or node.is_missing:
            return node.start_point.row + 1
        pending.extend(reversed(node.children))
    return None


def collect_definitions(
    matches: list[tuple[int, dict[str, list[tree_sitter.Node]]]], aliases: dict[str, str]
) -> list[Definition]:
    found: dict[tuple[int, int], Definition] = {}
    for _index, captures in matches:
        capture = capture_prefix_of(captures, DEFINITION_PREFIX)
        if capture is None or 'name' not in captures:
            continue

        node = captures[capture][0]
        kind = KINDS[capture.removeprefix(DEFINITION_PREFIX)]
        parent_nodes = captures.get('parent')
        impl_nodes = captures.get('impl')
        definition = Definition(
            name=address_of(captures, aliases),
            kind=kind,
            node=node,
            parent=text_of(parent_nodes[0]) if parent_nodes is not None else None,
            impl=text_of(impl_nodes[0]) if impl_nodes is not None else None,
        )
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
    matches: list[tuple[int, dict[str, list[tree_sitter.Node]]]], aliases: dict[str, str]
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
    query_name: str
    deadline_seconds: float = 2.0
    aliases: dict[str, str] = field(default_factory=dict)
    strict: bool = False
    query: tree_sitter.Query = field(init=False)

    def __post_init__(self) -> None:
        query = tree_sitter.Query(self.grammar, load_query_source(self.query_name))
        object.__setattr__(self, 'query', query)

    def parse(self, source: SourceFile) -> FileSymbols:
        data = source.text.encode('utf-8')
        parser = tree_sitter.Parser(self.grammar)
        deadline = Deadline(expires_at=time.monotonic() + self.deadline_seconds)
        try:
            tree = parser.parse(create_reader(data), progress_callback=deadline)
        except ValueError:
            if not deadline.fired:
                raise
            tree = None
        if tree is None:
            note = f'{source.path}: parse stopped after the {self.deadline_seconds} s time limit'
            return FileSymbols(
                path=source.path, language=self.language, symbols=(), references=(), notes=(note,)
            )

        error_line = first_error_line(tree.root_node) if self.strict else None
        if error_line is not None:
            note = f'{source.path}: syntax error at line {error_line}'
            return FileSymbols(
                path=source.path, language=self.language, symbols=(), references=(), notes=(note,)
            )

        matches = tree_sitter.QueryCursor(self.query).matches(tree.root_node)
        definitions = collect_definitions(matches, self.aliases)
        return FileSymbols(
            path=source.path,
            language=self.language,
            symbols=tuple(build_symbols(definitions, LINE_BREAK.split(source.text))),
            references=collect_references(matches, self.aliases),
            notes=(),
        )


JAVASCRIPT_BACKEND = TreeSitterBackend(
    language='javascript',
    suffixes=frozenset({'.js', '.mjs', '.cjs', '.jsx'}),
    grammar=tree_sitter.Language(tree_sitter_javascript.language()),
    query_name='javascript',
)


TYPESCRIPT_BACKEND = TreeSitterBackend(
    language='typescript',
    suffixes=frozenset({'.ts', '.mts', '.cts'}),
    grammar=tree_sitter.Language(tree_sitter_typescript.language_typescript()),
    query_name='typescript',
)

TSX_BACKEND = TreeSitterBackend(
    language='tsx',
    suffixes=frozenset({'.tsx'}),
    grammar=tree_sitter.Language(tree_sitter_typescript.language_tsx()),
    query_name='typescript',
)

GO_BACKEND = TreeSitterBackend(
    language='go',
    suffixes=frozenset({'.go'}),
    grammar=tree_sitter.Language(tree_sitter_go.language()),
    query_name='go',
)

TERRAFORM_BACKEND = TreeSitterBackend(
    language='terraform',
    suffixes=frozenset({'.tf'}),
    grammar=tree_sitter.Language(tree_sitter_hcl.language()),
    query_name='terraform',
    aliases={'variable': 'var', 'locals': 'local'},
    strict=True,
)

RUST_BACKEND = TreeSitterBackend(
    language='rust',
    suffixes=frozenset({'.rs'}),
    grammar=tree_sitter.Language(tree_sitter_rust.language()),
    query_name='rust',
)
