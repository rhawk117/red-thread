"""Slicing under a budget: symbol output, notes and refusals that must fit the smallest budget."""

from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import pytest
from red_thread_navigate.budget import MIN_BUDGET, estimate_tokens, fit_to_budget
from red_thread_navigate.slice import SliceError
from red_thread_navigate.slice.policy import Refused, refusal_text
from red_thread_navigate.slice.views import Found, symbol_rungs
from red_thread_navigate.symbols import Symbol

from tests.navigate.samples import CORE, NAVIGATOR, long_class
from tests.navigate.symbols.samples import SourceDir

if TYPE_CHECKING:
    from pathlib import Path

LONG_DIRS = '/'.join(f'directory{number}' for number in range(14))
LONG_PATH = f'{LONG_DIRS}/{"x" * 26}target_module.py'
LONG_NAME = ('a_very_long_symbol_name_' * 4)[:80]
LONG_SUFFIX_PATH = f'{"a" * 50}.{"x" * 149}'
NEAR_NAMES = '\n\n'.join(f'def similar_name_{number}():\n    pass' for number in range(8))
TWENTY_NAME = f'{"f" * 17}.py'
TWENTY_TEXT = f'{"t" * 16}.txt'
TWENTY_BLOB = f'{"b" * 17}.py'
TWENTY_MISSING = f'{"m" * 17}.py'


def symbol_budget_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('budget', [40, 80, 150, 300])


def refusal_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        ('address', 'file_name'),
        [
            (f'{LONG_PATH}#{LONG_NAME}', 'target_module.py'),
            (f'{LONG_PATH}#nosuch', 'target_module.py'),
            (f'{LONG_PATH}#similar_name', 'target_module.py'),
            (f'{LONG_PATH}#L99', 'target_module.py'),
            (f'{LONG_DIRS}/notes.txt#nosuch', 'notes.txt'),
            (f'{LONG_DIRS}/link.py#L1', 'link.py'),
            (f'{LONG_DIRS}/blob.py#L1', 'blob.py'),
            (f'../{"o" * 191}.py#L1', 'o.py#L1'),
            (f'{"x" * 200}', 'xxxxxxx'),
        ],
    )


def whole_name_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        'address',
        [
            f'{LONG_DIRS}/{TWENTY_NAME}#nosuch',
            f'{LONG_DIRS}/{TWENTY_NAME}#L99',
            f'{LONG_DIRS}/{TWENTY_TEXT}#nosuch',
            f'{LONG_DIRS}/{TWENTY_BLOB}#L1',
            f'{LONG_DIRS}/{TWENTY_MISSING}#L1',
        ],
    )


@pytest.fixture
def source(tmp_path: Path) -> SourceDir:
    return SourceDir(root=tmp_path)


class TestSymbolOutput:
    @pytest.fixture
    def long(self, source: SourceDir) -> SourceDir:
        source.write('big.py', long_class())
        return source

    @symbol_budget_cases()
    def test_symbol_output_stays_within_the_budget(self, long: SourceDir, budget: int) -> None:
        text = NAVIGATOR.slice('big.py#Big', root=long.root, budget=budget)

        assert estimate_tokens(text) <= budget

    def test_many_notes_never_push_the_output_past_the_budget(self) -> None:
        notes = tuple(f'could not parse module_{number}.py cleanly' for number in range(30))
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
            path=PurePosixPath('big.py'),
            symbol=symbol,
            children=(),
            lines=('def go():', '    pass'),
            whole=True,
        )

        rungs = symbol_rungs((found,), notes, budget=64)

        assert estimate_tokens(fit_to_budget(rungs, budget=64).text) <= 64
        assert rungs[0][-1] == 'and 29 more notes'


def refuse(root: SourceDir, address: str) -> str:
    with pytest.raises(SliceError) as raised:
        NAVIGATOR.slice(address, root=root.root, budget=MIN_BUDGET)
    return str(raised.value)


class TestRefusalPaths:
    @pytest.fixture
    def deep(self, tmp_path: Path) -> SourceDir:
        root = SourceDir(root=tmp_path / 'root')
        root.write(LONG_PATH, NEAR_NAMES)
        root.write(f'{LONG_DIRS}/notes.txt', 'plain\n')
        outside = SourceDir(root=tmp_path).write('secret.py', CORE)
        root.root.joinpath(f'{LONG_DIRS}/link.py').symlink_to(outside)
        root.root.joinpath(f'{LONG_DIRS}/blob.py').write_bytes(b'\x00\x01\x02')
        return root

    @pytest.fixture
    def long_named(self, source: SourceDir) -> SourceDir:
        source.write(LONG_PATH, 'def similar_name():\n    pass\n')
        return source

    @pytest.fixture
    def long_suffixed(self, source: SourceDir) -> SourceDir:
        source.write(LONG_SUFFIX_PATH, 'plain\n')
        return source

    @pytest.fixture
    def twenty(self, tmp_path: Path) -> SourceDir:
        root = SourceDir(root=tmp_path)
        root.write(f'{LONG_DIRS}/{TWENTY_NAME}', NEAR_NAMES)
        root.write(f'{LONG_DIRS}/{TWENTY_TEXT}', 'plain\n')
        tmp_path.joinpath(LONG_DIRS, TWENTY_BLOB).write_bytes(b'\x00\x01')
        return root

    @pytest.fixture
    def near_names(self, source: SourceDir) -> SourceDir:
        source.write(LONG_PATH, NEAR_NAMES)
        return source

    @refusal_cases()
    def test_every_refusal_stays_within_the_minimum_budget(
        self, deep: SourceDir, address: str, file_name: str
    ) -> None:
        message = refuse(deep, address)

        assert estimate_tokens(message) <= MIN_BUDGET
        assert '...' in message
        assert file_name in message

    def test_a_cut_path_keeps_its_file_name_and_a_cut_name_keeps_its_start(
        self, long_named: SourceDir
    ) -> None:
        message = refuse(long_named, f'{LONG_PATH}#{LONG_NAME}')

        assert 'target_module.py' in message
        assert 'a_very_long' in message

    def test_a_long_extension_cannot_push_the_no_backend_refusal_past_the_budget(
        self, long_suffixed: SourceDir
    ) -> None:
        assert len(LONG_SUFFIX_PATH) == len(LONG_PATH) == 200
        assert len(LONG_NAME) == 80

        message = refuse(long_suffixed, f'{LONG_SUFFIX_PATH}#nosuch')

        assert estimate_tokens(message) <= MIN_BUDGET

    @whole_name_cases()
    def test_a_twenty_character_file_name_survives_whole_under_a_long_directory(
        self, twenty: SourceDir, address: str
    ) -> None:
        file_name = address.split('#', maxsplit=1)[0].rsplit('/', 1)[-1]
        assert len(file_name) == 20

        message = refuse(twenty, address)

        assert file_name in message
        assert estimate_tokens(message) <= MIN_BUDGET

    def test_the_path_is_cut_to_its_floor_before_a_nearest_name_is_dropped(
        self, near_names: SourceDir
    ) -> None:
        message = refuse(near_names, f'{LONG_PATH}#similar_nam')

        assert 'similar_name_' in message
        assert estimate_tokens(message) <= MIN_BUDGET


class TestRefusalNames:
    @pytest.fixture
    def similar(self, source: SourceDir) -> SourceDir:
        source.write('core.py', '\n\n'.join(f'def similar_name_{n}():\n    pass' for n in range(8)))
        return source

    @pytest.fixture
    def twenty_long_name(self, source: SourceDir) -> SourceDir:
        source.write(f'{LONG_DIRS}/{TWENTY_NAME}', f'def {LONG_NAME}():\n    pass\n')
        return source

    def test_a_long_nearest_name_is_cut_not_dropped(self, twenty_long_name: SourceDir) -> None:
        message = refuse(twenty_long_name, f'{LONG_DIRS}/{TWENTY_NAME}#{LONG_NAME[:-1]}')

        assert 'no similar name' not in message
        assert 'a_very_long' in message
        assert estimate_tokens(message) <= MIN_BUDGET

    def test_the_whole_message_is_cut_when_the_floors_still_overflow(self) -> None:
        refused = Refused(path=PurePosixPath('a' * 200), budget=MIN_BUDGET)

        message = refusal_text(f'<path> {"word " * 100}', refused=refused, name='')

        assert estimate_tokens(message) <= MIN_BUDGET
        assert message.endswith('...')

    def test_an_unknown_symbol_message_stays_within_a_small_budget(
        self, similar: SourceDir
    ) -> None:
        with pytest.raises(SliceError) as raised:
            NAVIGATOR.slice('core.py#similar_name', root=similar.root, budget=40)

        assert estimate_tokens(str(raised.value)) <= 40
