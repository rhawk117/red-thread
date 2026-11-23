"""The Python backend turns a source file into symbols, references and notes."""

from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import pytest
from red_thread_navigate.symbols.store import PYTHON_BACKEND, backend_for
from red_thread_navigate.walk import SourceFile

from tests.navigate.symbols.samples import BROKEN, SAMPLE

if TYPE_CHECKING:
    from red_thread_navigate.symbols import FileSymbols, Symbol

PATH = PurePosixPath('pkg/sample.py')


def parse(text: str) -> FileSymbols:
    return PYTHON_BACKEND.parse(SourceFile(path=PATH, text=text))


def find_symbol(parsed: FileSymbols, qualified_name: str, kind: str | None = None) -> Symbol:
    matches = [
        symbol
        for symbol in parsed.symbols
        if symbol.qualified_name == qualified_name and kind in {None, symbol.kind}
    ]
    assert len(matches) == 1
    return matches[0]


def kind_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        ('qualified_name', 'kind'),
        [
            pytest.param('decorate', 'function', id='function'),
            pytest.param('Outer', 'class', id='class'),
            pytest.param('Outer.method', 'method', id='method'),
            pytest.param('Outer.method.inner', 'function', id='method-nested'),
            pytest.param('Outer.Nested', 'class', id='nested-class'),
            pytest.param('Outer.Nested.deep', 'method', id='nested-method'),
            pytest.param('outer', 'function', id='async-function'),
            pytest.param('outer.inner', 'function', id='nested-function'),
        ],
    )


class TestSymbols:
    @pytest.fixture
    def parsed(self) -> FileSymbols:
        return parse(SAMPLE)

    @kind_cases()
    def test_each_definition_has_its_dotted_name_and_kind(
        self, parsed: FileSymbols, qualified_name: str, kind: str
    ) -> None:
        assert find_symbol(parsed, qualified_name).kind == kind

    def test_property_and_its_setter_are_properties(self, parsed: FileSymbols) -> None:
        sizes = [symbol for symbol in parsed.symbols if symbol.qualified_name == 'Outer.size']
        assert [symbol.kind for symbol in sizes] == ['property', 'property']

    def test_span_starts_at_the_first_decorator(self, parsed: FileSymbols) -> None:
        method = find_symbol(parsed, 'Outer.method')
        lines = SAMPLE.splitlines()
        assert lines[method.start_line - 1].strip() == '@decorate'
        assert lines[method.end_line - 1].strip() == 'return inner()'

    def test_signature_is_the_definition_line(self, parsed: FileSymbols) -> None:
        assert (
            find_symbol(parsed, 'Outer.method').signature == 'def method(self, item: int) -> int:'
        )

    def test_docstring_is_kept_or_none(self, parsed: FileSymbols) -> None:
        assert find_symbol(parsed, 'Outer').docstring == 'Outer docs.'
        assert find_symbol(parsed, 'decorate').docstring is None

    def test_parent_is_the_enclosing_qualified_name(self, parsed: FileSymbols) -> None:
        assert find_symbol(parsed, 'Outer.method.inner').parent == 'Outer.method'
        assert find_symbol(parsed, 'Outer').parent is None


class TestReferences:
    @pytest.fixture
    def lines_by_name(self) -> dict[str, list[int]]:
        grouped: dict[str, list[int]] = {}
        for reference in parse(SAMPLE).references:
            grouped.setdefault(reference.name, []).append(reference.line)
        return grouped

    def test_calls_attribute_reads_and_bare_names_are_references(
        self, lines_by_name: dict[str, list[int]]
    ) -> None:
        assert 'Outer' in lines_by_name
        assert 'method' in lines_by_name
        assert 'helper' in lines_by_name

    def test_definition_name_line_is_not_a_reference(
        self, lines_by_name: dict[str, list[int]]
    ) -> None:
        definition_line = SAMPLE.splitlines().index('def decorate(function):') + 1
        assert (
            definition_line not in lines_by_name['decorate']
            if 'decorate' in lines_by_name
            else True
        )
        use_line = SAMPLE.splitlines().index('    value = Outer()') + 1
        assert lines_by_name['Outer'] == [use_line]

    def test_reference_lines_are_one_based(self, lines_by_name: dict[str, list[int]]) -> None:
        use_line = SAMPLE.splitlines().index('    return value.method(1) + helper') + 1
        assert use_line in lines_by_name['helper']


class TestSyntaxError:
    def test_yields_no_symbols_and_a_note_naming_file_and_line(self) -> None:
        parsed = parse(BROKEN)
        assert parsed.symbols == ()
        assert len(parsed.notes) == 1
        assert str(PATH) in parsed.notes[0]
        assert 'line 5' in parsed.notes[0]


class TestBackendFor:
    def test_python_suffix_selects_the_python_backend(self) -> None:
        assert backend_for(PATH) is PYTHON_BACKEND

    def test_unknown_suffix_selects_nothing(self) -> None:
        assert backend_for(PurePosixPath('notes.txt')) is None
