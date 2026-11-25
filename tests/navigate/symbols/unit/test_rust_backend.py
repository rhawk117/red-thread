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
fn ret() -> T { make() }
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

ITEM_TYPE_USES_SAMPLE = """\
pub struct T;
pub struct W<X>(X);
const C: T = make();
static S: T = make();
type A = T;
type P = *const W<u8>;
type R = [W<u8>; 2];
type U = (W<u8>, u8);
"""

VALUE_USES_SAMPLE = """\
pub struct T;
const LIMIT: u32 = 3;
static COUNT: u32 = 1;
pub enum E { Start, Stop = 2 }
pub union U { a: u8 }
pub struct Pair(u8);
macro_rules! MACRO { () => {} }
impl T { const ASSOC: u32 = 4; }
fn locals(count: u32) -> u32 { let n = count + 1; n }
fn unit() { let x: T = T; }
fn limit() -> u32 { let m = LIMIT + 1; m }
"""


def value_position_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        'statement',
        [
            pytest.param('let a = NAME;', id='let-value'),
            pytest.param('let a = NAME + 1;', id='binary-left'),
            pytest.param('let a = 1 + NAME;', id='binary-right'),
            pytest.param('let a = -NAME;', id='unary'),
            pytest.param('NAME = 1;', id='assignment-left'),
            pytest.param('a = NAME;', id='assignment-right'),
            pytest.param('NAME += 1;', id='compound-left'),
            pytest.param('a += NAME;', id='compound-right'),
            pytest.param('let a = NAME as u8;', id='type-cast'),
            pytest.param('let a = 0..NAME;', id='range'),
            pytest.param('g(NAME);', id='arguments'),
            pytest.param('let a = [NAME];', id='array'),
            pytest.param('let a = (NAME, 1);', id='tuple'),
            pytest.param('let a = (NAME);', id='parenthesized'),
            pytest.param('{ NAME }', id='block'),
            pytest.param('NAME;', id='expression-statement'),
            pytest.param('return NAME;', id='return'),
            pytest.param('loop { break NAME; }', id='break'),
            pytest.param('let a = NAME?;', id='try'),
            pytest.param('let a = NAME.await;', id='await'),
            pytest.param('let a = NAME[0];', id='index'),
            pytest.param('let a = &NAME;', id='reference'),
            pytest.param('match a { _ => NAME }', id='match-arm'),
            pytest.param('let a = || NAME;', id='closure'),
            pytest.param('if NAME {}', id='if'),
            pytest.param('while NAME {}', id='while'),
            pytest.param('let a = m::NAME;', id='scoped'),
            pytest.param('let a = S { NAME };', id='shorthand-field'),
        ],
    )


TRAIT_IMPL_SELF_SAMPLE = """\
struct S;
impl std::fmt::Display for S {}
struct W<X>(X);
impl Clone for W<S> {}
"""

GENERIC_DECLARATION_SAMPLE = 'fn declares<T>() {}\n'


def reference_lines(parsed: FileSymbols, name: str) -> list[int]:
    return sorted(reference.line for reference in parsed.references if reference.name == name)


class TestTypeReferences:
    @pytest.fixture
    def type_uses(self) -> FileSymbols:
        return parse(TYPE_USES_SAMPLE)

    @pytest.fixture
    def generic_declaration(self) -> FileSymbols:
        return parse(GENERIC_DECLARATION_SAMPLE)

    def test_type_uses_in_every_position_are_references(self, type_uses: FileSymbols) -> None:
        assert reference_lines(type_uses, 'T') == [5, 6, 7, 8, 9, 10, 11, 12]

    def test_declarations_are_not_references(self, type_uses: FileSymbols) -> None:
        declaring = {
            reference.line
            for reference in type_uses.references
            if reference.name in {'T', 'E', 'A', 'Tr'} and reference.line <= 4
        }

        assert declaring == set()

    def test_generic_parameter_declaration_is_not_a_reference(
        self, generic_declaration: FileSymbols
    ) -> None:
        assert reference_lines(generic_declaration, 'T') == []


class TestNestedTypeReferences:
    @pytest.fixture
    def nested_type_uses(self) -> FileSymbols:
        return parse(NESTED_TYPE_USES_SAMPLE)

    @pytest.fixture
    def item_type_uses(self) -> FileSymbols:
        return parse(ITEM_TYPE_USES_SAMPLE)

    @pytest.fixture
    def trait_impl_self(self) -> FileSymbols:
        return parse(TRAIT_IMPL_SELF_SAMPLE)

    def test_nested_type_uses_are_references(self, nested_type_uses: FileSymbols) -> None:
        assert reference_lines(nested_type_uses, 'T') == [3, 4, 5, 6, 7, 8]

    def test_generic_heads_are_references(self, nested_type_uses: FileSymbols) -> None:
        assert reference_lines(nested_type_uses, 'W') == [9, 10, 11]

    def test_item_and_nested_type_positions_are_references(
        self, item_type_uses: FileSymbols
    ) -> None:
        assert reference_lines(item_type_uses, 'T') == [3, 4, 5]
        assert reference_lines(item_type_uses, 'W') == [6, 7, 8]

    def test_trait_impl_self_types_are_references(self, trait_impl_self: FileSymbols) -> None:
        assert reference_lines(trait_impl_self, 'S') == [2, 4]
        assert reference_lines(trait_impl_self, 'W') == [4]


class TestValueReferences:
    @pytest.fixture
    def value_uses(self) -> FileSymbols:
        return parse(VALUE_USES_SAMPLE)

    def test_lowercase_locals_are_not_references(self, value_uses: FileSymbols) -> None:
        names = {reference.name for reference in value_uses.references}

        assert not names & {'count', 'n', 'm', 'x'}

    def test_unit_struct_value_is_listed_once_per_line(self, value_uses: FileSymbols) -> None:
        assert reference_lines(value_uses, 'T').count(10) == 1

    def test_constant_in_expression_is_a_reference(self, value_uses: FileSymbols) -> None:
        assert reference_lines(value_uses, 'LIMIT') == [11]

    def test_declaring_lines_are_not_references(self, value_uses: FileSymbols) -> None:
        declared = {'LIMIT', 'COUNT', 'Start', 'Stop', 'ASSOC', 'U', 'Pair', 'MACRO'}
        lines = {r.line for r in value_uses.references if r.name in declared}

        assert lines <= {11}

    def statement_reference_lines(self, statement: str, name: str) -> list[int]:
        text = f'const LIMIT: u32 = 1;\nfn f() {{ {statement.replace("NAME", name)} }}\n'
        return reference_lines(parse(text), name)

    @value_position_cases()
    def test_a_capitalized_name_in_each_value_position_is_a_reference(self, statement: str) -> None:
        assert self.statement_reference_lines(statement, 'LIMIT') == [2]

    @value_position_cases()
    def test_a_lowercase_name_in_each_value_position_is_not_a_reference(
        self, statement: str
    ) -> None:
        assert self.statement_reference_lines(statement, 'limit') == []
