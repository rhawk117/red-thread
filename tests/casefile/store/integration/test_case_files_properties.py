"""DirectoryCaseRepository: case.md first, then the thread files by number, each read as written."""

from typing import TYPE_CHECKING

import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from msgspec.structs import replace
from red_thread_casefile.domain import order_thread
from red_thread_casefile.errors import CaseExistsError, CaseNotFoundError, UndecodableFileError
from red_thread_casefile.schemas import read_case_file, write_case_file
from red_thread_casefile.store import DirectoryCaseRepository

from tests.casefile.entries.strategies import entries, thread_names
from tests.casefile.ledger.builders import create_case, create_entry
from tests.casefile.ledger.markdown import name_file, write_case_text, write_thread_text

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_casefile.domain import Entry

type Threads = dict[str, list[Entry]]

SEPARATED = create_entry(seq=1, text='a\x85b\N{LINE SEPARATOR}c\N{PARAGRAPH SEPARATOR}d')
NO_CARRIAGE_RETURN = st.characters(blacklist_categories=('Cs',), blacklist_characters='\r')


def number_entries(written: list[Entry], thread: str | None) -> list[Entry]:
    return [replace(entry, seq=seq, thread=thread) for seq, entry in enumerate(written, 1)]


def is_undecodable(content: bytes) -> bool:
    try:
        content.decode('utf-8')
    except UnicodeDecodeError:
        return True
    return False


class TestCaseFilesProperties:
    entry_lists = st.lists(entries, max_size=3)
    threads = st.dictionaries(thread_names, entry_lists, max_size=3)
    stray_names = st.sets(st.text(alphabet='abcxyz', min_size=1, max_size=6), max_size=3)
    texts = st.text(alphabet=NO_CARRIAGE_RETURN, max_size=40)
    undecodable = st.binary(min_size=1, max_size=40).filter(is_undecodable)

    def create_repository(self, factory: pytest.TempPathFactory) -> DirectoryCaseRepository:
        return DirectoryCaseRepository(directory=factory.mktemp('case', numbered=True))

    def write_file(self, repository: DirectoryCaseRepository, name: str, text: str) -> Path:
        path = repository.directory.joinpath(name)
        path.write_text(text, encoding='utf-8')
        return path

    @pytest.mark.regression
    @given(own=entry_lists, threads=threads)
    @example(own=[SEPARATED], threads={'T1': [SEPARATED]})
    def test_entries_written_to_the_files_read_back_case_first_then_threads_by_number(
        self, tmp_path_factory: pytest.TempPathFactory, own: list[Entry], threads: Threads
    ) -> None:
        repository = self.create_repository(tmp_path_factory)
        in_case = number_entries(own, None)
        repository.create(write_case_text(create_case(), in_case))
        in_threads = {name: number_entries(written, name) for name, written in threads.items()}
        for name, written in in_threads.items():
            self.write_file(repository, name_file(name), write_thread_text(written))

        reading = read_case_file(repository.read())

        ordered = sorted(in_threads, key=order_thread)
        expected = [*in_case, *(entry for name in ordered for entry in in_threads[name])]
        assert reading.problems == ()
        assert list(reading.ledger.entries) == expected

    @given(numbers=st.sets(st.integers(min_value=1, max_value=30), max_size=4), strays=stray_names)
    def test_thread_files_are_listed_by_number_and_stray_files_after_them(
        self, tmp_path_factory: pytest.TempPathFactory, numbers: set[int], strays: set[str]
    ) -> None:
        repository = self.create_repository(tmp_path_factory)
        repository.create(write_case_file(create_case()))
        for stem in (*(f'T{number}' for number in numbers), *strays):
            self.write_file(repository, name_file(stem), '')

        names = [source.name for source in repository.read()]

        numbered = [name_file(f'T{number}') for number in sorted(numbers)]
        assert names == ['case.md', *numbered, *sorted(map(name_file, strays))]

    @given(text=texts)
    def test_a_file_reads_back_as_the_text_written_to_it(
        self, tmp_path_factory: pytest.TempPathFactory, text: str
    ) -> None:
        repository = self.create_repository(tmp_path_factory)
        repository.create(text)

        [source] = repository.read()

        assert (source.name, source.thread, source.text) == ('case.md', None, text)

    @given(text=texts)
    def test_any_case_md_reads_to_a_case_or_to_the_problems_that_stop_it(
        self, tmp_path_factory: pytest.TempPathFactory, text: str
    ) -> None:
        repository = self.create_repository(tmp_path_factory)
        repository.create(text)

        reading = read_case_file(repository.read())

        assert reading.case is not None or reading.problems

    @given(content=undecodable, thread=st.booleans())
    def test_a_file_that_is_not_utf8_is_named(
        self, tmp_path_factory: pytest.TempPathFactory, content: bytes, thread: bool
    ) -> None:
        repository = self.create_repository(tmp_path_factory)
        repository.create(write_case_file(create_case()))
        path = repository.directory.joinpath(name_file('T1' if thread else None))
        path.write_bytes(content)

        with pytest.raises(UndecodableFileError) as raised:
            repository.read()

        assert raised.value.path == path


class TestCaseDirectory:
    @pytest.fixture
    def repository(self, tmp_path: Path) -> DirectoryCaseRepository:
        return DirectoryCaseRepository(directory=tmp_path.joinpath('case'))

    def test_create_refuses_a_case_that_already_exists(
        self, repository: DirectoryCaseRepository
    ) -> None:
        repository.create('first')

        with pytest.raises(CaseExistsError):
            repository.create('second')

        [source] = repository.read()
        assert source.text == 'first'

    def test_a_directory_without_case_md_is_not_a_case(
        self, repository: DirectoryCaseRepository
    ) -> None:
        with pytest.raises(CaseNotFoundError) as raised:
            repository.read()

        assert raised.value.path == repository.directory
