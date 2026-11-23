"""Slicing real files: whole symbols, outlines, line ranges, ambiguity, refusals and the budget."""

from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import pytest
from red_thread_navigate.address import AddressError
from red_thread_navigate.budget import estimate_tokens, fit_to_budget
from red_thread_navigate.slice import WINDOW_LINES, SliceError, slice_address
from red_thread_navigate.slice.services import Refused, refusal_text
from red_thread_navigate.slice.views import Found, symbol_rungs
from red_thread_navigate.symbols import Symbol

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


def test_unknown_symbol_with_no_similar_name_names_map_as_the_next_step(tmp_path: Path) -> None:
    write(tmp_path, 'core.py', SHORT)

    with pytest.raises(SliceError) as raised:
        slice_address('core.py#zzzzzz', root=tmp_path, budget=BIG_BUDGET)

    assert str(raised.value).endswith('Next step: map core.py to see the names there.')


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


def test_many_notes_never_push_the_output_past_the_budget() -> None:
    notes = tuple(f'could not parse module_{number}.py cleanly' for number in range(30))
    path = PurePosixPath('big.py')
    symbol = Symbol(
        name='go',
        qualified_name='go',
        kind='function',
        start_line=1,
        end_line=2,
        signature='def go()',
        docstring=None,
        parent=None,
    )
    found = Found(
        path=path, symbol=symbol, children=(), lines=('def go():', '    pass'), whole=True
    )

    fitted = fit_to_budget(symbol_rungs((found,), notes), budget=64)

    assert estimate_tokens(fitted.text) <= 64
    assert 'and 28 more notes' in symbol_rungs((found,), notes)[0]


def test_unknown_symbol_message_stays_within_the_budget(tmp_path: Path) -> None:
    names = '\n\n'.join(f'def similar_name_{number}():\n    pass' for number in range(8))
    write(tmp_path, 'core.py', names)

    with pytest.raises(SliceError) as raised:
        slice_address('core.py#similar_name', root=tmp_path, budget=40)

    assert estimate_tokens(str(raised.value)) <= 40


MIN_BUDGET = 32
LONG_DIRS = '/'.join(f'directory{number}' for number in range(14))
LONG_PATH = f'{LONG_DIRS}/{"x" * 26}target_module.py'
LONG_NAME = ('a_very_long_symbol_name_' * 4)[:80]
LONG_SUFFIX_PATH = f'{"a" * 50}.{"x" * 149}'
NEAR_NAMES = '\n\n'.join(f'def similar_name_{number}():\n    pass' for number in range(8))


def refusal_cases() -> list[tuple[str, str]]:
    return [
        (f'{LONG_PATH}#{LONG_NAME}', 'target_module.py'),
        (f'{LONG_PATH}#nosuch', 'target_module.py'),
        (f'{LONG_PATH}#similar_name', 'target_module.py'),
        (f'{LONG_PATH}#L99', 'target_module.py'),
        (f'{LONG_DIRS}/notes.txt#nosuch', 'notes.txt'),
        (f'{LONG_DIRS}/link.py#L1', 'link.py'),
        (f'{LONG_DIRS}/blob.py#L1', 'blob.py'),
        (f'../{"o" * 191}.py#L1', 'o.py#L1'),
        (f'{"x" * 200}', 'xxxxxxx'),
    ]


@pytest.mark.parametrize(('address', 'file_name'), refusal_cases())
def test_every_refusal_stays_within_the_minimum_budget(
    tmp_path: Path, address: str, file_name: str
) -> None:
    root = tmp_path / 'root'
    write(root, LONG_PATH, NEAR_NAMES)
    write(root, f'{LONG_DIRS}/notes.txt', 'plain\n')
    write(tmp_path, 'secret.py', SHORT)
    root.joinpath(f'{LONG_DIRS}/link.py').symlink_to(tmp_path / 'secret.py')
    root.joinpath(f'{LONG_DIRS}/blob.py').write_bytes(b'\x00\x01\x02')

    with pytest.raises(SliceError) as raised:
        slice_address(address, root=root, budget=MIN_BUDGET)

    message = str(raised.value)
    assert estimate_tokens(message) <= MIN_BUDGET
    assert '...' in message
    assert file_name in message


def test_a_cut_path_keeps_its_file_name_and_a_cut_name_keeps_its_start(tmp_path: Path) -> None:
    write(tmp_path, LONG_PATH, 'def similar_name():\n    pass\n')

    with pytest.raises(SliceError) as raised:
        slice_address(f'{LONG_PATH}#{LONG_NAME}', root=tmp_path, budget=MIN_BUDGET)

    assert 'target_module.py' in str(raised.value)
    assert 'a_very_long' in str(raised.value)


def test_a_long_extension_cannot_push_the_no_backend_refusal_past_the_budget(
    tmp_path: Path,
) -> None:
    assert len(LONG_SUFFIX_PATH) == len(LONG_PATH) == 200
    assert len(LONG_NAME) == 80
    write(tmp_path, LONG_SUFFIX_PATH, 'plain\n')

    with pytest.raises(SliceError) as raised:
        slice_address(f'{LONG_SUFFIX_PATH}#nosuch', root=tmp_path, budget=MIN_BUDGET)

    assert estimate_tokens(str(raised.value)) <= MIN_BUDGET


TWENTY_NAME = f'{"f" * 17}.py'
TWENTY_TEXT = f'{"t" * 16}.txt'
TWENTY_BLOB = f'{"b" * 17}.py'
TWENTY_MISSING = f'{"m" * 17}.py'


def whole_name_cases() -> list[str]:
    return [
        f'{LONG_DIRS}/{TWENTY_NAME}#nosuch',
        f'{LONG_DIRS}/{TWENTY_NAME}#L99',
        f'{LONG_DIRS}/{TWENTY_TEXT}#nosuch',
        f'{LONG_DIRS}/{TWENTY_BLOB}#L1',
        f'{LONG_DIRS}/{TWENTY_MISSING}#L1',
    ]


@pytest.mark.parametrize('address', whole_name_cases())
def test_a_twenty_character_file_name_survives_whole_under_a_long_directory(
    tmp_path: Path, address: str
) -> None:
    file_name = address.split('#', maxsplit=1)[0].rsplit('/', 1)[-1]
    assert len(file_name) == 20
    write(tmp_path, f'{LONG_DIRS}/{TWENTY_NAME}', NEAR_NAMES)
    write(tmp_path, f'{LONG_DIRS}/{TWENTY_TEXT}', 'plain\n')
    tmp_path.joinpath(LONG_DIRS, TWENTY_BLOB).write_bytes(b'\x00\x01')

    with pytest.raises(SliceError) as raised:
        slice_address(address, root=tmp_path, budget=MIN_BUDGET)

    assert file_name in str(raised.value)
    assert estimate_tokens(str(raised.value)) <= MIN_BUDGET


def test_a_long_nearest_name_is_cut_not_dropped(tmp_path: Path) -> None:
    write(tmp_path, f'{LONG_DIRS}/{TWENTY_NAME}', f'def {LONG_NAME}():\n    pass\n')

    with pytest.raises(SliceError) as raised:
        slice_address(
            f'{LONG_DIRS}/{TWENTY_NAME}#{LONG_NAME[:-1]}', root=tmp_path, budget=MIN_BUDGET
        )

    message = str(raised.value)
    assert 'no similar name' not in message
    assert 'a_very_long' in message
    assert estimate_tokens(message) <= MIN_BUDGET


def test_the_path_is_cut_to_its_floor_before_a_nearest_name_is_dropped(tmp_path: Path) -> None:
    address = f'{LONG_PATH}#similar_nam'
    write(tmp_path, LONG_PATH, NEAR_NAMES)

    with pytest.raises(SliceError) as raised:
        slice_address(address, root=tmp_path, budget=MIN_BUDGET)

    assert 'similar_name_' in str(raised.value)
    assert estimate_tokens(str(raised.value)) <= MIN_BUDGET


def test_the_whole_message_is_cut_when_the_floors_still_overflow() -> None:
    refused = Refused(path=PurePosixPath('a' * 200), budget=MIN_BUDGET)

    message = refusal_text(f'<path> {"word " * 100}', refused=refused, name='')

    assert estimate_tokens(message) <= MIN_BUDGET
    assert message.endswith('...')
