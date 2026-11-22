"""The page store contract, written once for the fake and the directory adapter."""

from dataclasses import dataclass
from typing import Protocol

from red_thread_casefile.store import PageStore


class PageReader(Protocol):
    def read(self, name: str) -> str | None: ...


@dataclass(slots=True, kw_only=True, frozen=True)
class PageHarness:
    store: PageStore
    reader: PageReader


class PageStoreContract:
    class TestImplementation:
        def test_store_satisfies_the_protocol(self, harness: PageHarness) -> None:
            assert isinstance(harness.store, PageStore)

    class TestWrite:
        def test_a_written_page_is_read_back_whole(self, harness: PageHarness) -> None:
            text = '<p>caf\N{LATIN SMALL LETTER E WITH ACUTE}</p>\n\nsecond line\n'

            harness.store.write('board.html', text)

            assert harness.reader.read('board.html') == text

        def test_the_returned_path_ends_with_the_name(self, harness: PageHarness) -> None:
            written = harness.store.write('board.html', 'x')

            assert written.name == 'board.html'

        def test_a_name_with_a_folder_is_written_under_that_folder(
            self, harness: PageHarness
        ) -> None:
            written = harness.store.write('out/brief.md', '# brief\n')

            assert written.parts[-2:] == ('out', 'brief.md')
            assert harness.reader.read('out/brief.md') == '# brief\n'

        def test_writing_again_replaces_the_page_whole(self, harness: PageHarness) -> None:
            harness.store.write('out/brief.md', 'a much longer first version\n')

            harness.store.write('out/brief.md', 'short\n')

            assert harness.reader.read('out/brief.md') == 'short\n'

        def test_pages_with_different_names_do_not_disturb_each_other(
            self, harness: PageHarness
        ) -> None:
            harness.store.write('out/brief.md', 'brief')
            harness.store.write('out/brief.html', 'page')
            harness.store.write('board.html', 'board')

            assert harness.reader.read('out/brief.md') == 'brief'
            assert harness.reader.read('out/brief.html') == 'page'
            assert harness.reader.read('board.html') == 'board'

        def test_an_empty_page_is_stored_as_empty_and_not_as_missing(
            self, harness: PageHarness
        ) -> None:
            harness.store.write('empty.md', '')

            assert harness.reader.read('empty.md') == ''

    class TestUnwritten:
        def test_a_page_never_written_reads_as_missing(self, harness: PageHarness) -> None:
            assert harness.reader.read('never.md') is None
