"""The Rust backend turns a source file into symbols, with impl methods addressed by type."""

from importlib import resources
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import pytest
from red_thread_navigate.map.views import RankedFile, RankedSymbol, symbol_line
from red_thread_navigate.symbols.store import backend_for
from red_thread_navigate.walk import SourceFile

from tests.navigate.symbols.samples import RUST_SAMPLE

if TYPE_CHECKING:
    from red_thread_navigate.symbols import FileSymbols
    from red_thread_navigate.symbols.domain import Backend


def backend_at(path: PurePosixPath) -> Backend:
    backend = backend_for(path)
    assert backend is not None
    return backend


def parse(text: str) -> FileSymbols:
    return backend_at(PurePosixPath('src/lib.rs')).parse(
        SourceFile(path=PurePosixPath('src/lib.rs'), text=text)
    )


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
        assert backend_at(PurePosixPath('a/b.rs')).language == 'rust'


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


TRAIT_USES_SAMPLE = """\
pub trait Sink {}
pub struct Pipe;
impl Sink for Pipe {}
fn bound<T: Sink>(item: T) {}
fn clause<T>(item: T) where T: Sink {}
fn boxed(item: Box<dyn Sink>) {}
fn opaque(item: impl Sink) {}
"""


class TestTraitReferences:
    def test_trait_uses_in_headers_bounds_and_types_are_references(self) -> None:
        parsed = parse(TRAIT_USES_SAMPLE)

        lines = sorted(
            reference.line for reference in parsed.references if reference.name == 'Sink'
        )

        assert lines == [3, 4, 5, 6, 7]


TYPE_USES_SAMPLE = """\
pub struct T;
pub enum E {}
pub type A = u8;
pub trait Tr {}
fn param(x: T) {}
fn ret() -> T { T }
fn annotated() { let y: T = make(); }
pub struct Holder { field: T }
fn generic(v: Vec<T>) {}
fn literal() { let z = T { a: 1 }; }
fn scoped(w: m::T) {}
fn declares<T>(item: T) {}
"""

NESTED_TYPE_USES_SAMPLE = """\
pub struct T;
pub struct W<X>(X);
fn refs(a: &T, b: &mut T) {}
fn pointer(p: *const T) {}
fn array(xs: [T; 3]) {}
fn tuple(pair: (T, u8)) {}
fn option(o: Option<&T>) {}
impl T { fn new() {} }
fn param(w: W<u8>) {}
fn ret() -> W<u8> { make() }
pub struct Holder { field: W<u8> }
"""


class TestTypeReferences:
    def test_type_uses_in_every_position_are_references(self) -> None:
        parsed = parse(TYPE_USES_SAMPLE)

        lines = sorted({reference.line for reference in parsed.references if reference.name == 'T'})

        assert lines == [5, 6, 7, 8, 9, 10, 11, 12]

    def test_nested_type_uses_are_references(self) -> None:
        parsed = parse(NESTED_TYPE_USES_SAMPLE)

        lines = sorted({reference.line for reference in parsed.references if reference.name == 'T'})

        assert lines == [3, 4, 5, 6, 7, 8]

    def test_generic_heads_are_references(self) -> None:
        parsed = parse(NESTED_TYPE_USES_SAMPLE)

        lines = sorted({reference.line for reference in parsed.references if reference.name == 'W'})

        assert lines == [9, 10, 11]

    def test_trait_impl_self_types_are_references(self) -> None:
        parsed = parse(
            'struct S;\nimpl std::fmt::Display for S {}\nstruct W<X>(X);\nimpl Clone for W<S> {}\n'
        )

        s_lines = sorted({r.line for r in parsed.references if r.name == 'S'})
        w_lines = sorted({r.line for r in parsed.references if r.name == 'W'})

        assert s_lines == [2, 4]
        assert w_lines == [4]

    def test_declarations_are_not_references(self) -> None:
        parsed = parse(TYPE_USES_SAMPLE)

        names = {
            (reference.name, reference.line)
            for reference in parsed.references
            if reference.name in {'T', 'E', 'A', 'Tr'}
        }

        assert not {name for name in names if name[1] <= 4}

    def test_generic_parameter_declaration_is_not_a_reference(self) -> None:
        parsed = parse('fn declares<T>() {}\n')

        assert [r for r in parsed.references if r.name == 'T'] == []
