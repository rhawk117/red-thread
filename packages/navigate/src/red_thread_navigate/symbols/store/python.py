import ast
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_navigate.symbols.domain import FileSymbols, Reference, Symbol

if TYPE_CHECKING:
    from collections.abc import Sequence

    from red_thread_navigate.symbols.domain import SymbolKind
    from red_thread_navigate.walk import SourceFile

type Definition = ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef

LINE_BREAK = re.compile(r'\r\n|\r|\n')
PROPERTY_ACCESSORS = frozenset({'setter', 'getter', 'deleter'})


@dataclass(slots=True, kw_only=True, frozen=True)
class Scope:
    qualified_name: str | None
    in_class: bool


def decorator_marks_property(decorator: ast.expr) -> bool:
    if isinstance(decorator, ast.Name):
        return decorator.id == 'property'
    if isinstance(decorator, ast.Attribute):
        return decorator.attr in PROPERTY_ACCESSORS
    return False


def kind_of(node: Definition, scope: Scope) -> SymbolKind:
    if isinstance(node, ast.ClassDef):
        return 'class'
    if not scope.in_class:
        return 'function'
    if any(decorator_marks_property(decorator) for decorator in node.decorator_list):
        return 'property'
    return 'method'


def start_line_of(node: Definition) -> int:
    return min([node.lineno, *(decorator.lineno for decorator in node.decorator_list)])


def build_symbol(node: Definition, scope: Scope, lines: list[str]) -> Symbol:
    qualified_name = (
        node.name if scope.qualified_name is None else f'{scope.qualified_name}.{node.name}'
    )
    return Symbol(
        name=node.name,
        qualified_name=qualified_name,
        kind=kind_of(node, scope),
        start_line=start_line_of(node),
        end_line=node.end_lineno or node.lineno,
        signature=lines[node.lineno - 1].strip(),
        docstring=ast.get_docstring(node),
        parent=scope.qualified_name,
    )


def collect_symbols(nodes: Sequence[ast.AST], scope: Scope, lines: list[str]) -> list[Symbol]:
    symbols: list[Symbol] = []
    for node in nodes:
        symbols.extend(symbols_of(node, scope, lines))
    return symbols


def symbols_of(node: ast.AST, scope: Scope, lines: list[str]) -> list[Symbol]:
    if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
        symbol = build_symbol(node, scope, lines)
        inner = Scope(qualified_name=symbol.qualified_name, in_class=isinstance(node, ast.ClassDef))
        return [symbol, *collect_symbols(node.body, inner, lines)]
    nested = [
        child
        for child in ast.iter_child_nodes(node)
        if isinstance(child, ast.stmt | ast.excepthandler | ast.match_case)
    ]
    return collect_symbols(nested, scope, lines)


def collect_references(tree: ast.Module) -> tuple[Reference, ...]:
    references: list[Reference] = []
    augmented = {
        id(node.target)
        for node in ast.walk(tree)
        if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Attribute)
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            references.append(Reference(name=node.id, line=node.lineno))
        elif isinstance(node, ast.Attribute) and (
            isinstance(node.ctx, ast.Load) or id(node) in augmented
        ):
            references.append(Reference(name=node.attr, line=node.end_lineno or node.lineno))
    return tuple(sorted(references, key=lambda reference: (reference.line, reference.name)))


@dataclass(slots=True, kw_only=True, frozen=True)
class PythonBackend:
    language: str = 'python'
    suffixes: frozenset[str] = frozenset({'.py', '.pyi'})

    def parse(self, source: SourceFile) -> FileSymbols:
        try:
            tree = ast.parse(source.text, filename=str(source.path))
        except SyntaxError as error:
            note = f'{source.path}: syntax error at line {error.lineno}: {error.msg}'
            return FileSymbols(
                path=source.path, language=self.language, symbols=(), references=(), notes=(note,)
            )
        scope = Scope(qualified_name=None, in_class=False)
        symbols = collect_symbols(tree.body, scope, LINE_BREAK.split(source.text))
        return FileSymbols(
            path=source.path,
            language=self.language,
            symbols=tuple(symbols),
            references=collect_references(tree),
            notes=(),
        )


PYTHON_BACKEND = PythonBackend()
