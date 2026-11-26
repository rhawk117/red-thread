"""The JavaScript backend turns a source file into symbols, references and notes."""

import dataclasses
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import pytest
from red_thread_navigate.symbols.store import backend_for
from red_thread_navigate.symbols.store.treesitter import TreeSitterBackend
from red_thread_navigate.walk import SourceFile

from tests.navigate.symbols.samples import JAVASCRIPT_SAMPLE

if TYPE_CHECKING:
    from red_thread_navigate.symbols import FileSymbols
    from red_thread_navigate.symbols.domain import Backend

PATH = PurePosixPath('web/sample.js')


def backend_at(path: PurePosixPath) -> Backend:
    backend = backend_for(path)
    assert backend
    return backend


def parse(text: str, backend: Backend | None = None) -> FileSymbols:
    backend = backend or backend_at(PATH)
    return backend.parse(SourceFile(path=PATH, text=text))


def symbol_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        ('qualified_name', 'kind', 'span'),
        [
            pytest.param('Widget', 'class', (1, 9), id='class'),
            pytest.param('Widget.render', 'method', (6, 8), id='method'),
            pytest.param('build', 'function', (11, 13), id='function-declaration'),
            pytest.param('arrow', 'function', (15, 15), id='arrow-const'),
            pytest.param('bound', 'function', (17, 19), id='function-expression-const'),
            pytest.param('Exported', 'class', (21, 25), id='exported-class'),
            pytest.param('Exported.open', 'method', (22, 24), id='exported-method'),
            pytest.param('exportedFunction', 'function', (27, 29), id='exported-function'),
            pytest.param('exportedArrow', 'function', (31, 31), id='exported-arrow'),
        ],
    )


def javascript_suffix_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('suffix', ['.js', '.mjs', '.cjs', '.jsx'])


class TestSymbols:
    @pytest.fixture
    def parsed(self) -> FileSymbols:
        return parse(JAVASCRIPT_SAMPLE)

    @symbol_cases()
    def test_each_definition_has_its_dotted_name_kind_and_span(
        self, parsed: FileSymbols, qualified_name: str, kind: str, span: tuple[int, int]
    ) -> None:
        matches = [symbol for symbol in parsed.symbols if symbol.qualified_name == qualified_name]
        assert len(matches) == 1
        assert (matches[0].kind, (matches[0].start_line, matches[0].end_line)) == (kind, span)

    def test_constructor_is_not_a_symbol(self, parsed: FileSymbols) -> None:
        assert 'Widget.constructor' not in {symbol.qualified_name for symbol in parsed.symbols}

    def test_method_names_its_class_as_parent(self, parsed: FileSymbols) -> None:
        render = next(s for s in parsed.symbols if s.qualified_name == 'Widget.render')
        assert (render.name, render.parent) == ('render', 'Widget')


class TestReferences:
    def test_calls_and_constructions_are_reported_with_their_lines(self) -> None:
        parsed = parse(JAVASCRIPT_SAMPLE)
        found = {(reference.name, reference.line) for reference in parsed.references}
        assert {('helper', 7), ('Widget', 12), ('arrow', 18), ('render', 23)} <= found


class TestSyntaxError:
    def test_keeps_the_symbols_that_parse_and_names_the_first_error_line(self) -> None:
        parsed = parse(JAVASCRIPT_SAMPLE + '\nfunction broken( {\n')
        names = {symbol.qualified_name for symbol in parsed.symbols}
        assert {'Widget', 'Widget.render'} <= names
        assert parsed.notes == ('web/sample.js: syntax error at line 33',)


class TestTimeLimit:
    def test_parse_past_the_deadline_yields_a_note_naming_file_and_limit(self) -> None:
        original = backend_at(PATH)
        assert isinstance(original, TreeSitterBackend)
        backend = dataclasses.replace(original, deadline_seconds=1e-9)
        parsed = parse('[' * 200_000 + ']' * 200_000, backend)
        assert (parsed.symbols, parsed.references) == ((), ())
        assert len(parsed.notes) == 1
        assert 'web/sample.js' in parsed.notes[0]
        assert '1e-09' in parsed.notes[0]


class TestLookup:
    @javascript_suffix_cases()
    def test_backend_for_finds_javascript_suffixes(self, suffix: str) -> None:
        assert backend_at(PurePosixPath(f'a{suffix}')).language == 'javascript'


ASSIGNED_SAMPLE = """\
app.init = function init() {
  app.get('/', function getrouter() {});
};

View.prototype.lookup = function lookup(name) {
  return name;
};
"""


class TestAssignedFunctions:
    @pytest.fixture
    def parsed(self) -> FileSymbols:
        return parse(ASSIGNED_SAMPLE)

    def test_each_assignment_is_one_symbol_named_as_its_target_is_written(
        self, parsed: FileSymbols
    ) -> None:
        names = [symbol.qualified_name for symbol in parsed.symbols]
        assert names == ['app.init', 'View.prototype.lookup']

    def test_a_function_passed_as_an_argument_is_not_a_symbol(self, parsed: FileSymbols) -> None:
        assert all('getrouter' not in symbol.qualified_name for symbol in parsed.symbols)


class TestExportedFunctionExpression:
    def test_an_exported_const_function_expression_is_a_function(self) -> None:
        parsed = parse('export const f = function () {}\n')
        spans = [
            (symbol.kind, symbol.start_line, symbol.end_line)
            for symbol in parsed.symbols
            if symbol.qualified_name == 'f'
        ]
        assert spans == [('function', 1, 1)]


class TestGeneratorConstants:
    def test_generator_valued_const_is_a_function(self) -> None:
        parsed = parse('const gen = function* () {}\n')
        spans = [
            (symbol.kind, symbol.start_line, symbol.end_line)
            for symbol in parsed.symbols
            if symbol.qualified_name == 'gen'
        ]
        assert spans == [('function', 1, 1)]
