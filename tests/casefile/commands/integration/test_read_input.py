"""read_input over real files."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.cli import read_input
from red_thread_casefile.errors import UnreadableInputError

if TYPE_CHECKING:
    from pathlib import Path


class TestReadInput:
    def test_a_file_is_read_whole_as_utf_8(self, tmp_path: Path) -> None:
        text = '[{"text": "caf\N{LATIN SMALL LETTER E WITH ACUTE}"}]\n'
        source = tmp_path.joinpath('batch.json')
        source.write_text(text, encoding='utf-8')

        assert read_input(str(source)) == text

    def test_a_missing_file_raises_with_its_path_and_a_reason(self, tmp_path: Path) -> None:
        missing = tmp_path.joinpath('nothing.json')

        with pytest.raises(UnreadableInputError) as raised:
            read_input(str(missing))

        assert raised.value.path == str(missing)
        assert raised.value.reason
        assert 'cannot be read' in str(raised.value)

    def test_a_directory_raises_the_same_error(self, tmp_path: Path) -> None:
        with pytest.raises(UnreadableInputError) as raised:
            read_input(str(tmp_path))

        assert raised.value.path == str(tmp_path)

    def test_a_file_that_is_not_utf_8_is_not_swallowed_as_unreadable_text(
        self, tmp_path: Path
    ) -> None:
        source = tmp_path.joinpath('latin.json')
        source.write_bytes(b'\xe9')

        with pytest.raises(UnicodeDecodeError):
            read_input(str(source))
