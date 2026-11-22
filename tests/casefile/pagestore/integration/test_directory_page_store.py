"""The page store contract against a directory on disk, and what lands on disk."""

from typing import TYPE_CHECKING

from red_thread_casefile.store import DirectoryPageStore

from tests.casefile.pagestore.page_store_suite import PageStoreContract

if TYPE_CHECKING:
    from pathlib import Path


class TestDirectoryPageStore(PageStoreContract):
    pass


class TestOnDisk:
    def test_the_returned_path_is_the_file_inside_the_directory(self, tmp_path: Path) -> None:
        store = DirectoryPageStore(directory=tmp_path.joinpath('case'))

        written = store.write('out/brief.md', 'x')

        assert written == tmp_path.joinpath('case', 'out', 'brief.md')
        assert written.read_text(encoding='utf-8') == 'x'

    def test_the_file_is_written_as_utf_8(self, tmp_path: Path) -> None:
        store = DirectoryPageStore(directory=tmp_path)
        text = 'caf\N{LATIN SMALL LETTER E WITH ACUTE} \N{EM DASH} \N{SNOWMAN}\n'

        written = store.write('board.html', text)

        assert written.read_bytes() == text.encode('utf-8')

    def test_the_directory_and_its_parents_are_created_on_the_first_write(
        self, tmp_path: Path
    ) -> None:
        directory = tmp_path.joinpath('deeper', 'still', 'case')
        assert not directory.exists()

        DirectoryPageStore(directory=directory).write('out/brief.md', 'x')

        assert directory.joinpath('out').is_dir()

    def test_existing_files_beside_the_page_are_left_alone(self, tmp_path: Path) -> None:
        tmp_path.joinpath('case.json').write_text('{}', encoding='utf-8')

        DirectoryPageStore(directory=tmp_path).write('out/brief.md', 'x')

        assert tmp_path.joinpath('case.json').read_text(encoding='utf-8') == '{}'
