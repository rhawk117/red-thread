"""The Rust backend turns a source file into symbols, with impl methods addressed by type."""

from importlib import resources
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import pytest
from red_thread_navigate.map.views import RankedFile, RankedSymbol, symbol_line
from red_thread_navigate.symbols.store import RUST_BACKEND, backend_for
from red_thread_navigate.walk import SourceFile

from tests.navigate.symbols.samples import RUST_SAMPLE

if TYPE_CHECKING:
    from red_thread_navigate.symbols import FileSymbols


def parse(text: str) -> FileSymbols:
    return RUST_BACKEND.parse(SourceFile(path=PurePosixPath('src/lib.rs'), text=text))


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
            pytest.param('LIMIT', [('constant', 3, 3)], id='constant'),
            pytest.param('Wrapper', [('struct', 5, 7)], id='struct'),
            pytest.param('Color', [('enum', 9, 11)], id='enum'),
            pytest.param('Shape', [('trait', 13, 15)], id='trait'),
            pytest.param('Shape.area', [('method', 14, 14)], id='trait-methods'),
            pytest.param('Wrapper.new', [('method', 18, 20)], id='generic-inherent-method'),
            pytest.param('Color.fmt', [('method', 24, 26), ('method', 30, 32)], id='trait-impls'),
            pytest.param('build', [('function', 41, 43)], id='function'),
        ],
    )


class TestSymbols:
    @pytest.fixture
    def parsed(self) -> FileSymbols:
        return parse(RUST_SAMPLE)

    @symbol_cases()
    def test_each_definition_has_its_address_kind_and_span(
        self, parsed: FileSymbols, qualified_name: str, expected: list[tuple[str, int, int]]
    ) -> None:
        assert spans_of(parsed, qualified_name) == expected

    def test_an_inherent_method_leaves_the_impl_empty(self, parsed: FileSymbols) -> None:
        new = next(s for s in parsed.symbols if s.qualified_name == 'Wrapper.new')
        assert new.impl is None

    def test_trait_impls_of_one_method_name_are_told_apart(self, parsed: FileSymbols) -> None:
        impls = sorted(s.impl or '' for s in parsed.symbols if s.qualified_name == 'Color.fmt')
        assert impls == ['fmt::Debug', 'fmt::Display']

    def test_a_method_in_an_impl_on_a_reference_is_addressed_by_the_type(
        self, parsed: FileSymbols
    ) -> None:
        impl_methods = [s for s in parsed.symbols if s.qualified_name == 'Color.area']
        assert [s.impl for s in impl_methods] == ['Shape']

    def test_map_prints_the_impl_in_the_label(self, parsed: FileSymbols) -> None:
        method = next(s for s in parsed.symbols if s.qualified_name == 'Color.area')
        ranked = RankedSymbol(symbol=method, references=0)
        line = symbol_line(RankedFile(file=parsed, symbols=(ranked,)), ranked)
        assert 'method (impl Shape) fn area(&self) -> f64 {' in line

    def test_rust_files_pick_the_rust_backend(self) -> None:
        assert backend_for(PurePosixPath('a/b.rs')) is RUST_BACKEND


class TestQuery:
    def test_query_carries_the_upstream_notice_and_loads_as_a_resource(self) -> None:
        text = (
            resources
            .files('red_thread_navigate.symbols.store')
            .joinpath('queries', 'rust.scm')
            .read_text(encoding='utf-8')
        )
        assert 'Copyright (c) 2017 Maxim Sokolov' in text
        assert 'The MIT License (MIT)' in text
