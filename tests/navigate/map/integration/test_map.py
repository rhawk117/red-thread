"""Mapping a real directory: ranking by references, budget rungs, notes and the empty case."""

from typing import TYPE_CHECKING

from red_thread_navigate.budget import estimate_tokens
from red_thread_navigate.cli import create_navigator

if TYPE_CHECKING:
    from pathlib import Path

CORE = """\
def helper():
    return 1


def rarely():
    return 2


class Widget:
    def render(self):
        return helper()
"""
CLIENT = """\
from core import helper


def run():
    helper()
    helper()
"""
BIG_BUDGET = 10_000
NAVIGATOR = create_navigator()


def write(root: Path, name: str, text: str) -> None:
    target = root.joinpath(name)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8')


def test_directory_lists_symbols_with_addresses_most_referenced_first(tmp_path: Path) -> None:
    write(tmp_path, 'core.py', CORE)
    write(tmp_path, 'client.py', CLIENT)

    text = NAVIGATOR.map(tmp_path, budget=BIG_BUDGET)

    assert 'core.py#Widget.render' in text
    assert 'L1-L2' in text
    assert text.index('core.py#helper') < text.index('core.py#rarely')
    assert text.index('core.py  ') < text.index('client.py  ')


def test_file_lists_its_full_outline(tmp_path: Path) -> None:
    write(tmp_path, 'core.py', CORE)
    write(tmp_path, 'client.py', CLIENT)

    text = NAVIGATOR.map(tmp_path / 'core.py', budget=BIG_BUDGET)

    assert 'client.py' not in text
    assert all(
        address in text
        for address in (
            'core.py#helper',
            'core.py#rarely',
            'core.py#Widget',
            'core.py#Widget.render',
        )
    )


def test_small_budget_steps_down_and_keeps_the_most_referenced_file(tmp_path: Path) -> None:
    for number in range(40):
        write(tmp_path, f'm{number:02}.py', f'def f{number}():\n    return 1\n')
    write(tmp_path, 'zz_hot.py', 'def hot():\n    pass\n\n\ndef use():\n    hot()\n    hot()\n')

    full = NAVIGATOR.map(tmp_path, budget=BIG_BUDGET)
    small = NAVIGATOR.map(tmp_path, budget=150)

    assert 'zz_hot.py#hot' in full
    assert '#' not in small
    assert 'zz_hot.py' in small.splitlines()[1]
    assert 'raise --budget' in small


def test_notes_come_first_and_survive_a_cut(tmp_path: Path) -> None:
    write(tmp_path, 'broken.py', 'def (:\n')
    for number in range(40):
        write(tmp_path, f'm{number:02}.py', f'def f{number}():\n    return 1\n')
    tmp_path.joinpath('blob.bin').write_bytes(b'\0\1\2')

    text = NAVIGATOR.map(tmp_path, budget=64)

    lines = text.splitlines()
    assert lines[0].startswith('skipped 1 binary')
    assert 'broken.py: syntax error' in lines[1]
    assert 'raise --budget' in text


def test_empty_directory_names_languages_suffixes_and_next_step(tmp_path: Path) -> None:
    write(tmp_path, 'notes.txt', 'hello\n')

    text = NAVIGATOR.map(tmp_path, budget=BIG_BUDGET)

    assert 'No file navigate can read' in text
    assert 'python (.py, .pyi)' in text
    assert 'javascript (.cjs, .js, .jsx, .mjs)' in text
    assert 'Next step' in text


def test_many_unparsable_files_stay_within_the_budget(tmp_path: Path) -> None:
    for number in range(30):
        write(tmp_path, f'bad{number:02}.py', 'def (:\n')

    text = NAVIGATOR.map(tmp_path, budget=64)

    assert estimate_tokens(text) <= 64
    assert 'more notes' in text


def test_empty_path_message_is_fitted_to_the_budget(tmp_path: Path) -> None:
    write(tmp_path, 'notes.txt', 'hello\n')

    text = NAVIGATOR.map(tmp_path, budget=32)

    assert estimate_tokens(text) <= 32


def test_file_outline_is_in_source_order(tmp_path: Path) -> None:
    write(tmp_path, 'core.py', CORE)
    write(tmp_path, 'client.py', CLIENT)

    text = NAVIGATOR.map(tmp_path / 'core.py', budget=BIG_BUDGET)

    assert (
        text.index('core.py#helper') < text.index('core.py#rarely') < text.index('core.py#Widget')
    )
