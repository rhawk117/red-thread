"""create_exclusive: a new file is written, an existing one is reported and kept."""

from typing import TYPE_CHECKING

from red_thread_core.store import create_exclusive

if TYPE_CHECKING:
    from pathlib import Path


class TestCreateExclusive:
    def test_a_new_file_is_written_and_nothing_is_returned(self, tmp_path: Path) -> None:
        path = tmp_path.joinpath('case.md')

        assert create_exclusive(path, 'x') is None

        assert path.read_text(encoding='utf-8') == 'x'

    def test_an_existing_file_is_reported_and_keeps_its_content(self, tmp_path: Path) -> None:
        path = tmp_path.joinpath('case.md')
        path.write_text('old', encoding='utf-8')

        error = create_exclusive(path, 'new')

        assert isinstance(error, FileExistsError)
        assert path.read_text(encoding='utf-8') == 'old'

    def test_missing_parent_directories_are_created(self, tmp_path: Path) -> None:
        path = tmp_path.joinpath('deeper', 'still', 'case.md')

        assert create_exclusive(path, 'x') is None

        assert path.read_text(encoding='utf-8') == 'x'
