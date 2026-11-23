"""The Go backend turns a source file into symbols, with methods addressed by receiver."""

import dataclasses
from importlib import resources
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import pytest
import tree_sitter
from red_thread_navigate.symbols.store import GO_BACKEND, backend_for
from red_thread_navigate.walk import SourceFile

from tests.navigate.symbols.samples import GO_SAMPLE

if TYPE_CHECKING:
    from red_thread_navigate.symbols import FileSymbols


def parse(text: str) -> FileSymbols:
    return GO_BACKEND.parse(SourceFile(path=PurePosixPath('shapes/shapes.go'), text=text))


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
            pytest.param('Pi', [('constant', 3, 3)], id='constant'),
            pytest.param('Shape', [('interface', 5, 7)], id='interface'),
            pytest.param('Shape.Area', [('method', 6, 6)], id='interface-method'),
            pytest.param('Circle', [('struct', 9, 11)], id='struct'),
            pytest.param('ID', [('type', 13, 13)], id='defined-type'),
            pytest.param('Circle.Area', [('method', 15, 17)], id='value-receiver-method'),
            pytest.param('Build', [('function', 19, 21)], id='function'),
            pytest.param('Circle.Grow', [('method', 23, 25)], id='pointer-receiver-method'),
        ],
    )


class TestSymbols:
    @pytest.fixture
    def parsed(self) -> FileSymbols:
        return parse(GO_SAMPLE)

    @symbol_cases()
    def test_each_definition_has_its_address_kind_and_span(
        self, parsed: FileSymbols, qualified_name: str, expected: list[tuple[str, int, int]]
    ) -> None:
        assert spans_of(parsed, qualified_name) == expected

    def test_a_method_names_its_receiver_type_as_parent(self, parsed: FileSymbols) -> None:
        parents = {s.qualified_name: s.parent for s in parsed.symbols if s.kind == 'method'}
        assert parents['Circle.Grow'] == 'Circle'

    def test_a_method_declared_before_its_type_keeps_the_receiver_address(self) -> None:
        text = 'package p\n\nfunc (t *T) Run() {}\n\ntype T struct{}\n'
        assert spans_of(parse(text), 'T.Run') == [('method', 3, 3)]

    def test_a_generic_receiver_is_addressed_by_its_base_type(self) -> None:
        text = 'package p\n\ntype T[V any] struct{}\n\nfunc (t *T[V]) Run() {}\n'
        assert spans_of(parse(text), 'T.Run') == [('method', 5, 5)]

    def test_go_files_pick_the_go_backend(self) -> None:
        assert backend_for(PurePosixPath('a/b.go')) is GO_BACKEND


class TestQuery:
    def test_query_carries_the_upstream_notice_and_loads_as_a_resource(self) -> None:
        text = (
            resources
            .files('red_thread_navigate.symbols.store')
            .joinpath('queries', 'go.scm')
            .read_text(encoding='utf-8')
        )
        assert 'Copyright (c) 2014 Max Brunsfeld' in text
        assert 'The MIT License (MIT)' in text


class TestTimeLimit:
    def test_a_parse_failure_other_than_the_deadline_is_not_reported_as_a_time_out(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fail(*_args: object, **_kwargs: object) -> tree_sitter.Tree:
            message = 'unreadable source'
            raise ValueError(message)

        monkeypatch.setattr(tree_sitter.Parser, 'parse', fail)
        backend = dataclasses.replace(GO_BACKEND, deadline_seconds=60.0)
        source = SourceFile(path=PurePosixPath('a.go'), text=GO_SAMPLE)
        parsed = backend.parse(source)
        assert parsed.symbols == ()
        assert len(parsed.notes) == 1
        assert 'unreadable source' in parsed.notes[0]
        assert 'time limit' not in parsed.notes[0]


TYPE_USE_SAMPLE = """package shapes

type Handler struct{}

func serve(h Handler) {
	_ = Handler{}
}
"""


class TestTypeReferences:
    def test_parameter_and_composite_literal_types_are_references_at_their_lines(self) -> None:
        lines = [r.line for r in parse(TYPE_USE_SAMPLE).references if r.name == 'Handler']
        assert {5, 6} <= set(lines)
