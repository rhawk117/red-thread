"""Finding a name in a real directory: definitions first, references, no match and the budget."""

from typing import TYPE_CHECKING

import pytest
from red_thread_navigate.budget import estimate_tokens, fit_notes
from red_thread_navigate.cli import create_navigator

if TYPE_CHECKING:
    from pathlib import Path

CORE = """\
def helper():
    return 1


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
SMALL_BUDGET = 40


def write(root: Path, name: str, text: str) -> None:
    target = root.joinpath(name)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8')


def test_definitions_come_before_references(tmp_path: Path) -> None:
    write(tmp_path, 'core.py', CORE)
    write(tmp_path, 'client.py', CLIENT)

    text = NAVIGATOR.find('helper', tmp_path, budget=BIG_BUDGET)

    assert 'core.py#helper  function  L1-L2' in text
    assert 'client.py:5' in text
    assert 'client.py:6' in text
    assert 'core.py:7' in text
    assert text.index('core.py#helper') < text.index('client.py:5')


def test_dotted_name_matches_the_qualified_ending(tmp_path: Path) -> None:
    write(tmp_path, 'core.py', CORE)

    text = NAVIGATOR.find('Widget.render', tmp_path, budget=BIG_BUDGET)

    assert 'core.py#Widget.render  method' in text


def test_unknown_name_suggests_a_next_step(tmp_path: Path) -> None:
    write(tmp_path, 'core.py', CORE)

    text = NAVIGATOR.find('missing', tmp_path, budget=BIG_BUDGET)

    assert f'no matches for missing in {tmp_path}' in text
    assert f'map {tmp_path}' in text
    assert f'rg missing {tmp_path}' in text


@pytest.mark.parametrize('budget', [SMALL_BUDGET, 60, 120])
def test_output_stays_within_budget_and_says_it_was_cut(tmp_path: Path, budget: int) -> None:
    write(tmp_path, 'core.py', CORE)
    for index in range(60):
        write(tmp_path, f'client{index}.py', CLIENT)

    text = NAVIGATOR.find('helper', tmp_path, budget=budget)

    assert estimate_tokens(text) <= budget
    assert 'raise --budget' in text


def test_crowding_notes_are_cut_and_counted() -> None:
    notes = tuple(f'note number {index} about a file' for index in range(20))

    kept = fit_notes(notes, budget=100)

    assert kept[-1].endswith('more notes')
    assert kept[0] == 'note number 0 about a file'
    assert estimate_tokens('\n'.join(kept)) <= 100 // 4 + estimate_tokens(kept[-1])


def test_a_syntax_error_note_too_long_for_its_share_is_still_counted(tmp_path: Path) -> None:
    write(tmp_path, 'broken.py', 'def (:\n')

    text = NAVIGATOR.find('helper', tmp_path, budget=40)

    assert 'and 1 more notes' in text


@pytest.mark.parametrize('name', ['helper', 'missing'])
@pytest.mark.parametrize('budget', [SMALL_BUDGET, 64, 200])
def test_many_notes_keep_the_whole_output_within_budget(
    tmp_path: Path, name: str, budget: int
) -> None:
    write(tmp_path, 'core.py', CORE)
    for index in range(30):
        write(tmp_path, f'broken{index}.py', 'def (:\n')

    text = NAVIGATOR.find(name, tmp_path, budget=budget)

    assert estimate_tokens(text) <= budget
