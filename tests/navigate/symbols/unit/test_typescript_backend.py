"""The TypeScript and TSX backends turn a source file into symbols."""

from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import pytest
from red_thread_navigate.symbols.store import backend_for
from red_thread_navigate.walk import SourceFile

from tests.navigate.symbols.samples import TSX_SAMPLE, TYPESCRIPT_SAMPLE, spans_of

if TYPE_CHECKING:
    from red_thread_navigate.symbols import FileSymbols
    from red_thread_navigate.symbols.domain import Backend


def backend_at(suffix: str) -> Backend:
    backend = backend_for(PurePosixPath(f'web/sample{suffix}'))
    assert backend
    return backend


def parse(text: str, suffix: str) -> FileSymbols:
    source = SourceFile(path=PurePosixPath('web/sample.ts'), text=text)
    return backend_at(suffix).parse(source)


CONSTANTS_SAMPLE = """const LIMIT = 5
let count = 0
var legacy = 1
const handler = () => LIMIT
export const isSomeElementSelected = (function () {
  const cache = 1
  function ret() {}
  return ret
})()
export let total: number
function work() {
  const inside = 1
  let again = 2
}
"""


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
        return parse(TYPESCRIPT_SAMPLE, '.ts')

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


def module_constant_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        ('qualified_name', 'expected'),
        [
            pytest.param('LIMIT', [('constant', 1, 1)], id='const'),
            pytest.param('count', [('variable', 2, 2)], id='let'),
            pytest.param('legacy', [('variable', 3, 3)], id='var'),
            pytest.param('handler', [('function', 4, 4)], id='function-valued-const'),
            pytest.param('isSomeElementSelected', [('constant', 5, 9)], id='exported-iife'),
            pytest.param('isSomeElementSelected.ret', [('function', 7, 7)], id='iife-inner'),
            pytest.param('total', [('variable', 10, 10)], id='exported-let-without-value'),
        ],
    )


def other_value_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        ('text', 'suffix', 'name', 'kind'),
        [
            pytest.param(
                'const asserted = <number>raw',
                '.ts',
                'asserted',
                'constant',
                id='angle-assertion',
            ),
            pytest.param(
                'const cast = raw as Config',
                '.ts',
                'cast',
                'constant',
                id='as-assertion',
            ),
            pytest.param('const self = this', '.ts', 'self', 'constant', id='this'),
            pytest.param(
                'export const meta = import.meta',
                '.ts',
                'meta',
                'constant',
                id='import-meta',
            ),
            pytest.param(
                'let later = import.meta.url',
                '.ts',
                'later',
                'variable',
                id='let-import-meta',
            ),
            pytest.param('var old = <number>raw', '.ts', 'old', 'variable', id='var-assertion'),
            pytest.param(
                'const icon = <span />', '.tsx', 'icon', 'constant', id='jsx-self-closing'
            ),
            pytest.param(
                'export const box = <div>hi</div>', '.tsx', 'box', 'constant', id='jsx-element'
            ),
            pytest.param('let frag = <></>', '.tsx', 'frag', 'variable', id='jsx-fragment'),
            pytest.param(
                'const named = function () {}',
                '.ts',
                'named',
                'function',
                id='function-expression',
            ),
        ],
    )


def inner_declaration_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('name', ['cache', 'inside', 'again'])


def typescript_suffix_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('suffix', ['.ts', '.mts', '.cts'])


def generator_suffix_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('suffix', ['.ts', '.tsx'], ids=['ts', 'tsx'])


class TestModuleConstants:
    @pytest.fixture
    def parsed(self) -> FileSymbols:
        return parse(CONSTANTS_SAMPLE, '.ts')

    @module_constant_cases()
    def test_top_level_declarations_are_symbols_with_their_span(
        self, parsed: FileSymbols, qualified_name: str, expected: list[tuple[str, int, int]]
    ) -> None:
        assert spans_of(parsed, qualified_name) == expected

    @inner_declaration_cases()
    def test_declarations_inside_functions_add_no_symbols(
        self, parsed: FileSymbols, name: str
    ) -> None:
        assert not [s for s in parsed.symbols if s.name == name]

    @other_value_cases()
    def test_constants_are_symbols_whatever_their_non_function_value(
        self, text: str, suffix: str, name: str, kind: str
    ) -> None:
        assert spans_of(parse(text, suffix), name) == [(kind, 1, 1)]

    def test_tsx_files_get_the_same_constants(self) -> None:
        parsed = parse(CONSTANTS_SAMPLE, '.tsx')
        assert spans_of(parsed, 'LIMIT') == [('constant', 1, 1)]


class TestTsx:
    def test_components_are_symbols_with_their_addresses(self) -> None:
        parsed = parse(TSX_SAMPLE, '.tsx')
        found = {(s.qualified_name, s.kind, s.start_line, s.end_line) for s in parsed.symbols}
        assert found == {
            ('Greeting', 'function', 1, 3),
            ('Badge', 'function', 5, 5),
            ('Page', 'function', 7, 9),
        }


class TestLookup:
    @typescript_suffix_cases()
    def test_backend_for_finds_typescript_suffixes(self, suffix: str) -> None:
        assert backend_at(suffix).language == 'typescript'

    def test_backend_for_finds_tsx(self) -> None:
        assert backend_at('.tsx').language == 'tsx'


class TestGeneratorConstants:
    @generator_suffix_cases()
    def test_generator_valued_const_is_a_function(self, suffix: str) -> None:
        parsed = parse('const gen = function* () {}\n', suffix)
        assert spans_of(parsed, 'gen') == [('function', 1, 1)]
