"""Slicing real files: whole symbols, outlines, dotted addresses and line ranges."""

from typing import TYPE_CHECKING

import pytest
from red_thread_navigate.budget import estimate_tokens
from red_thread_navigate.cli import create_navigator
from red_thread_navigate.slice import WINDOW_LINES

from tests.navigate.symbols.samples import SourceDir

if TYPE_CHECKING:
    from pathlib import Path

SHORT = """\
def helper():
    return 1


class Widget:
    def render(self):
        return helper()
"""
TWICE = 'def go():\n    return 1\n\n\ndef go():\n    return 2\n'
ASSIGNED = """\
app.init = function init() {
  return 1;
};

View.prototype.lookup = function lookup(name) {
  return name;
};
"""
NOTES = '\n'.join(f'line {number}' for number in range(1, 400))
BIG_BUDGET = 10_000
NAVIGATOR = create_navigator()


def long_class() -> str:
    body = '\n'.join(f'        total += {number}' for number in range(WINDOW_LINES))
    return (
        'class Big:\n'
        '    """A long class."""\n\n'
        '    def first(self):\n'
        f'        total = 0\n{body}\n'
        '        return total\n\n'
        '    def second(self):\n'
        '        return 2\n'
    )


def dotted_address_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        ('address', 'heading', 'first_line'),
        [
            pytest.param(
                'app.js#app.init',
                'app.js#app.init  function  L1-L3  at the top level',
                '1: app.init = function init() {',
                id='member',
            ),
            pytest.param(
                'app.js#View.prototype.lookup',
                'app.js#View.prototype.lookup  function  L5-L7  at the top level',
                '5: View.prototype.lookup = function lookup(name) {',
                id='prototype-member',
            ),
        ],
    )


@pytest.fixture
def source(tmp_path: Path) -> SourceDir:
    return SourceDir(root=tmp_path)


class TestWholeSymbols:
    @pytest.fixture
    def short(self, source: SourceDir) -> SourceDir:
        source.write('core.py', SHORT)
        return source

    @pytest.fixture
    def long(self, source: SourceDir) -> SourceDir:
        source.write('big.py', long_class())
        return source

    @pytest.fixture
    def twice(self, source: SourceDir) -> SourceDir:
        source.write('twice.py', TWICE)
        return source

    @pytest.fixture
    def assigned(self, source: SourceDir) -> SourceDir:
        source.write('app.js', ASSIGNED)
        return source

    def test_short_symbol_comes_back_whole_with_line_numbers(self, short: SourceDir) -> None:
        text = NAVIGATOR.slice('core.py#Widget', root=short.root, budget=BIG_BUDGET)

        assert '5: class Widget:' in text
        assert '7:         return helper()' in text
        assert 'body:' not in text

    def test_long_symbol_comes_back_as_an_outline_with_addresses(self, long: SourceDir) -> None:
        text = NAVIGATOR.slice('big.py#Big', root=long.root, budget=BIG_BUDGET)

        assert 'A long class.' in text
        assert 'big.py#Big.first' in text
        assert 'big.py#Big.second' in text
        assert 'body: big.py#L1-L' in text
        assert 'total += 5' not in text

    def test_several_definitions_are_all_returned_with_parent_and_span(
        self, twice: SourceDir
    ) -> None:
        text = NAVIGATOR.slice('twice.py#go', root=twice.root, budget=BIG_BUDGET)

        assert '2 definitions match' in text
        assert 'L1-L2' in text
        assert 'L5-L6' in text
        assert 'at the top level' in text

    @dotted_address_cases()
    def test_a_dotted_javascript_address_slices_the_assigned_function(
        self, assigned: SourceDir, address: str, heading: str, first_line: str
    ) -> None:
        lines = NAVIGATOR.slice(address, root=assigned.root, budget=BIG_BUDGET).splitlines()

        assert lines[0] == heading
        assert lines[1] == first_line
        assert len(lines) == 4


class TestLineRanges:
    @pytest.fixture
    def notes(self, source: SourceDir) -> SourceDir:
        source.write('notes.txt', NOTES)
        return source

    def test_a_range_on_any_text_file_comes_back_exactly(self, notes: SourceDir) -> None:
        exact = NAVIGATOR.slice('notes.txt#L3-L5', root=notes.root, budget=BIG_BUDGET)

        assert exact.splitlines() == ['notes.txt#L3-L5', '3: line 3', '4: line 4', '5: line 5']

    def test_a_range_is_cut_only_by_the_budget(self, notes: SourceDir) -> None:
        small = NAVIGATOR.slice('notes.txt#L1-L399', root=notes.root, budget=64)

        assert 'raise --budget' in small
        assert estimate_tokens(small) <= 64
