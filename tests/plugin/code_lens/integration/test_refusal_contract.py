"""agents/code-lens.md and the navigate package agree on the markers a refusal carries."""

import re
from typing import TYPE_CHECKING

import pytest
from red_thread_navigate.find import find_name
from red_thread_navigate.slice import slice_address

if TYPE_CHECKING:
    from pathlib import Path

MARKERS = ('cannot be sliced:', 'Next step:', 'nearest names:', 'is not valid:')
BUDGET = 1500


def slice_refusals(root: Path) -> tuple[str, ...]:
    addresses = (
        'noseparator',
        'core.py#',
        'core.py#nosuch',
        'core.py#helpr',
        'core.py#L99',
        'notes.txt#nosuch',
        'blob.py#L1',
        'big.py#L1',
        'latin.py#L1',
        'src#thing',
        '../outside.py#L1',
    )
    messages = []
    for address in addresses:
        with pytest.raises(ValueError, match=r'\S') as raised:
            slice_address(address, root=root, budget=BUDGET)
        messages.append(str(raised.value))
    return tuple(messages)


def find_refusal(root: Path) -> str:
    return find_name('nosuch', root, budget=BUDGET)


class TestRefusalContract:
    @pytest.fixture
    def root(self, tmp_path: Path) -> Path:
        tree = tmp_path / 'root'
        tree.joinpath('src').mkdir(parents=True)
        tree.joinpath('core.py').write_text('def helper():\n    return 1\n', encoding='utf-8')
        tree.joinpath('notes.txt').write_text('plain\n', encoding='utf-8')
        tree.joinpath('blob.py').write_bytes(b'\x00\x01\x02')
        tree.joinpath('big.py').write_text('x = 1\n' * 200_000, encoding='utf-8')
        tree.joinpath('latin.py').write_bytes('caf\xe9 = 1\n'.encode('latin-1'))
        return tree

    @pytest.fixture
    def refusals(self, root: Path) -> tuple[str, ...]:
        return (*slice_refusals(root), find_refusal(root))

    @pytest.fixture
    def named_in_prompt(self, repository_root: Path) -> tuple[str, ...]:
        prompt = repository_root.joinpath('agents', 'code-lens.md').read_text(encoding='utf-8')
        spans = re.findall(r'`([^`]*)`', prompt)
        return tuple(marker for marker in MARKERS if any(marker in span for span in spans))

    @pytest.fixture
    def printed(self, refusals: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(marker for marker in MARKERS if any(marker in text for text in refusals))

    def test_every_refusal_carries_a_marker(self, refusals: tuple[str, ...]) -> None:
        unmarked = [text for text in refusals if not any(marker in text for marker in MARKERS)]

        assert unmarked == []

    def test_every_marker_the_package_prints_is_named_in_the_prompt(
        self, printed: tuple[str, ...], named_in_prompt: tuple[str, ...]
    ) -> None:
        assert set(printed) <= set(named_in_prompt)

    def test_every_marker_the_prompt_names_is_still_printed(
        self, printed: tuple[str, ...], named_in_prompt: tuple[str, ...]
    ) -> None:
        assert set(named_in_prompt) <= set(printed)
