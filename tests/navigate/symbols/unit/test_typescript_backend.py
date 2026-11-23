"""The TypeScript and TSX backends turn a source file into symbols."""

from importlib import resources
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import pytest
from red_thread_navigate.symbols.store import TSX_BACKEND, TYPESCRIPT_BACKEND, backend_for
from red_thread_navigate.walk import SourceFile

from tests.navigate.symbols.samples import TSX_SAMPLE, TYPESCRIPT_SAMPLE

if TYPE_CHECKING:
    from red_thread_navigate.symbols import FileSymbols
    from red_thread_navigate.symbols.store.treesitter import TreeSitterBackend


def parse(text: str, backend: TreeSitterBackend) -> FileSymbols:
    return backend.parse(SourceFile(path=PurePosixPath('web/sample.ts'), text=text))


def spans_of(parsed: FileSymbols, qualified_name: str) -> list[tuple[str, int, int]]:
    return sorted(
        (symbol.kind, symbol.start_line, symbol.end_line)
        for symbol in parsed.symbols
        if symbol.qualified_name == qualified_name
    )


def symbol_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        ('qualified_name', 'expected'),
        [
            pytest.param('Shape', [('interface', 1, 3)], id='interface'),
            pytest.param('Shape.area', [('method', 2, 2)], id='interface-method'),
            pytest.param('Id', [('type', 5, 5)], id='type-alias'),
            pytest.param('Color', [('enum', 7, 10)], id='enum'),
            pytest.param('Circle', [('class', 12, 16)], id='class'),
            pytest.param('Circle.area', [('method', 13, 15)], id='method'),
            pytest.param('arrow', [('function', 24, 24)], id='arrow-const'),
            pytest.param('Store', [('class', 26, 30)], id='exported-class'),
        ],
    )


class TestSymbols:
    @pytest.fixture
    def parsed(self) -> FileSymbols:
        return parse(TYPESCRIPT_SAMPLE, TYPESCRIPT_BACKEND)

    @symbol_cases()
    def test_each_definition_has_its_dotted_name_kind_and_span(
        self, parsed: FileSymbols, qualified_name: str, expected: list[tuple[str, int, int]]
    ) -> None:
        assert spans_of(parsed, qualified_name) == expected

    def test_each_function_overload_is_its_own_symbol_at_the_same_address(
        self, parsed: FileSymbols
    ) -> None:
        assert spans_of(parsed, 'build') == [
            ('function', 18, 18),
            ('function', 19, 19),
            ('function', 20, 22),
        ]

    def test_overloads_differ_by_signature(self, parsed: FileSymbols) -> None:
        signatures = {s.signature for s in parsed.symbols if s.qualified_name == 'build'}
        assert len(signatures) == 3

    def test_each_method_overload_is_its_own_symbol(self, parsed: FileSymbols) -> None:
        assert spans_of(parsed, 'Store.put') == [
            ('method', 27, 27),
            ('method', 28, 28),
            ('method', 29, 29),
        ]


class TestTsx:
    def test_components_are_symbols_with_their_addresses(self) -> None:
        parsed = parse(TSX_SAMPLE, TSX_BACKEND)
        found = {(s.qualified_name, s.kind, s.start_line, s.end_line) for s in parsed.symbols}
        assert found == {
            ('Greeting', 'function', 1, 3),
            ('Badge', 'function', 5, 5),
            ('Page', 'function', 7, 9),
        }


class TestLookup:
    @pytest.mark.parametrize('suffix', ['.ts', '.mts', '.cts'])
    def test_backend_for_finds_typescript_suffixes(self, suffix: str) -> None:
        assert backend_for(PurePosixPath(f'a{suffix}')) is TYPESCRIPT_BACKEND

    def test_backend_for_finds_tsx(self) -> None:
        assert backend_for(PurePosixPath('a.tsx')) is TSX_BACKEND

    def test_query_loads_with_the_upstream_license_notice(self) -> None:
        query = (
            resources
            .files('red_thread_navigate.symbols.store')
            .joinpath('queries', 'typescript.scm')
            .read_text(encoding='utf-8')
        )
        assert 'Max Brunsfeld' in query
        assert 'MIT License' in query
