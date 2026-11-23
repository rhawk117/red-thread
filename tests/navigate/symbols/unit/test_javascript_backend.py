"""The JavaScript backend turns a source file into symbols, references and notes."""

import dataclasses
from importlib import resources
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import pytest
from red_thread_navigate.symbols.store import JAVASCRIPT_BACKEND, backend_for
from red_thread_navigate.walk import SourceFile

from tests.navigate.symbols.samples import JAVASCRIPT_SAMPLE

if TYPE_CHECKING:
    from red_thread_navigate.symbols import FileSymbols
    from red_thread_navigate.symbols.store.treesitter import TreeSitterBackend

PATH = PurePosixPath('web/sample.js')


def parse(text: str, backend: TreeSitterBackend = JAVASCRIPT_BACKEND) -> FileSymbols:
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
        assert len(parsed.notes) == 1
        assert 'web/sample.js' in parsed.notes[0]
        assert 'syntax error at line' in parsed.notes[0]


class TestTimeLimit:
    def test_parse_past_the_deadline_yields_a_note_naming_file_and_limit(self) -> None:
        backend = dataclasses.replace(JAVASCRIPT_BACKEND, deadline_seconds=1e-9)
        parsed = parse('[' * 200_000 + ']' * 200_000, backend)
        assert (parsed.symbols, parsed.references) == ((), ())
        assert len(parsed.notes) == 1
        assert 'web/sample.js' in parsed.notes[0]
        assert '1e-09' in parsed.notes[0]


class TestLookup:
    @pytest.mark.parametrize('suffix', ['.js', '.mjs', '.cjs', '.jsx'])
    def test_backend_for_finds_javascript_suffixes(self, suffix: str) -> None:
        assert backend_for(PurePosixPath(f'a{suffix}')) is JAVASCRIPT_BACKEND

    def test_query_loads_with_the_upstream_license_notice(self) -> None:
        query = (
            resources
            .files('red_thread_navigate.symbols.store')
            .joinpath('queries', 'javascript.scm')
            .read_text(encoding='utf-8')
        )
        assert 'Max Brunsfeld' in query
        assert 'MIT License' in query
