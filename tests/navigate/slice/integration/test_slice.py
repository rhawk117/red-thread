"""Slicing real files: whole symbols, outlines, line ranges, ambiguity, refusals and the budget."""

from typing import TYPE_CHECKING

import pytest
from red_thread_navigate.address import AddressError
from red_thread_navigate.budget import estimate_tokens
from red_thread_navigate.slice import WINDOW_LINES, SliceError, slice_address

if TYPE_CHECKING:
    from pathlib import Path

SHORT = """\
def helper():
    return 1


class Widget:
    def render(self):
        return helper()
"""
BIG_BUDGET = 10_000


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


def write(root: Path, name: str, text: str) -> None:
    target = root.joinpath(name)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8')


def test_short_symbol_comes_back_whole_with_line_numbers(tmp_path: Path) -> None:
    write(tmp_path, 'core.py', SHORT)

    text = slice_address('core.py#Widget', root=tmp_path, budget=BIG_BUDGET)

    assert '5: class Widget:' in text
    assert '7:         return helper()' in text
    assert 'body:' not in text


def test_long_symbol_comes_back_as_an_outline_with_addresses(tmp_path: Path) -> None:
    write(tmp_path, 'big.py', long_class())

    text = slice_address('big.py#Big', root=tmp_path, budget=BIG_BUDGET)

    assert 'A long class.' in text
    assert 'big.py#Big.first' in text
    assert 'big.py#Big.second' in text
    assert 'body: big.py#L1-L' in text
    assert 'total += 5' not in text


def test_line_range_on_any_text_file_is_cut_only_by_the_budget(tmp_path: Path) -> None:
    write(tmp_path, 'notes.txt', '\n'.join(f'line {number}' for number in range(1, 400)))

    exact = slice_address('notes.txt#L3-L5', root=tmp_path, budget=BIG_BUDGET)
    small = slice_address('notes.txt#L1-L399', root=tmp_path, budget=64)

    assert exact.splitlines() == ['notes.txt#L3-L5', '3: line 3', '4: line 4', '5: line 5']
    assert 'raise --budget' in small
    assert estimate_tokens(small) <= 64


def test_several_definitions_are_all_returned_with_parent_and_span(tmp_path: Path) -> None:
    write(tmp_path, 'twice.py', 'def go():\n    return 1\n\n\ndef go():\n    return 2\n')

    text = slice_address('twice.py#go', root=tmp_path, budget=BIG_BUDGET)

    assert '2 definitions match' in text
    assert 'L1-L2' in text
    assert 'L5-L6' in text
    assert 'at the top level' in text


def test_unknown_symbol_is_refused_with_the_nearest_names(tmp_path: Path) -> None:
    write(tmp_path, 'core.py', SHORT)

    with pytest.raises(SliceError, match=r'nearest names: .*helper'):
        slice_address('core.py#helpr', root=tmp_path, budget=BIG_BUDGET)


def test_lines_past_the_end_are_refused(tmp_path: Path) -> None:
    write(tmp_path, 'core.py', SHORT)

    with pytest.raises(SliceError, match='past its end'):
        slice_address('core.py#L50', root=tmp_path, budget=BIG_BUDGET)


def test_symlink_leaving_the_root_is_refused(tmp_path: Path) -> None:
    root = tmp_path / 'root'
    root.mkdir()
    write(tmp_path, 'secret.py', SHORT)
    root.joinpath('link.py').symlink_to(tmp_path / 'secret.py')

    with pytest.raises(SliceError, match='outside the root'):
        slice_address('link.py#L1-L2', root=root, budget=BIG_BUDGET)


def test_address_outside_the_root_is_refused(tmp_path: Path) -> None:
    with pytest.raises(AddressError):
        slice_address('../x.py#L1', root=tmp_path, budget=BIG_BUDGET)


@pytest.mark.parametrize('budget', [40, 80, 150, 300])
def test_symbol_output_stays_within_the_budget(tmp_path: Path, budget: int) -> None:
    write(tmp_path, 'big.py', long_class())

    text = slice_address('big.py#Big', root=tmp_path, budget=budget)

    assert estimate_tokens(text) <= budget
