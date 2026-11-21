"""DirectoryCaseRepository: appended entries read back in order, and a corrupt file names itself."""

import json
from itertools import chain
from typing import TYPE_CHECKING

import msgspec
import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from red_thread_casefile.domain import order_thread
from red_thread_casefile.errors import CorruptCaseError, CorruptLedgerError
from red_thread_casefile.schemas import entry_to_line
from red_thread_casefile.store import DirectoryCaseRepository

from tests.casefile.entries.strategies import POOLED_THREADS, entries
from tests.casefile.services.fakes import CASE, create_entry

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_casefile.domain import Entry


type Batches = list[tuple[str | None, list[Entry]]]

SEPARATED = create_entry(seq=1, text='a\x85b\N{LINE SEPARATOR}c\N{PARAGRAPH SEPARATOR}d')
LINE_SAFE = st.characters(blacklist_categories=('Cs',), blacklist_characters='\r\n')


class TestLedgerFilesProperties:
    batches = st.lists(
        st.tuples(st.sampled_from(POOLED_THREADS), st.lists(entries, max_size=3)), max_size=5
    )
    threads = st.sampled_from((None, 'T1', 'T10'))
    blanks = st.integers(min_value=0, max_value=3)
    scalars = st.one_of(st.none(), st.booleans(), st.integers(), st.text(max_size=10))
    corrupt_values = st.one_of(
        scalars,
        st.lists(st.integers(), max_size=3),
        st.dictionaries(st.text(max_size=5), scalars, max_size=3),
    )
    not_json = st.text(alphabet=LINE_SAFE, min_size=1, max_size=20).filter(str.strip)

    def create_repository(self, factory: pytest.TempPathFactory) -> DirectoryCaseRepository:
        repository = DirectoryCaseRepository(directory=factory.mktemp('case', numbered=True))
        repository.create(CASE)
        return repository

    def locate(self, repository: DirectoryCaseRepository, thread: str | None) -> Path:
        if thread is None:
            return repository.directory.joinpath('ledger.jsonl')
        return repository.directory.joinpath('threads', f'{thread}.jsonl')

    def write_lines(self, path: Path, lines: list[str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    def expect_corrupt_line(
        self, factory: pytest.TempPathFactory, thread: str | None, lines: list[str], number: int
    ) -> None:
        repository = self.create_repository(factory)
        path = self.locate(repository, thread)
        self.write_lines(path, lines)

        with pytest.raises(CorruptLedgerError) as raised:
            repository.read_ledger()

        assert raised.value.path == path
        assert raised.value.line_number == number

    @pytest.mark.regression
    @given(batches=batches)
    @example(batches=[(None, [SEPARATED]), ('T1', [SEPARATED])])
    def test_what_is_appended_reads_back_unchanged_in_order_across_threads(
        self, tmp_path_factory: pytest.TempPathFactory, batches: Batches
    ) -> None:
        repository = self.create_repository(tmp_path_factory)

        for thread, batch in batches:
            repository.append(thread, tuple(batch))

        named = sorted({thread for thread, _ in batches if thread is not None}, key=order_thread)
        expected = [
            msgspec.structs.replace(entry, thread=thread)
            for thread in (None, *named)
            for entry in chain.from_iterable(b for t, b in batches if t == thread)
        ]
        assert list(repository.read_ledger().entries) == expected

    @pytest.mark.regression
    @given(thread=threads, blanks=blanks, good=st.lists(entries, max_size=3), bad=corrupt_values)
    @example(thread=None, blanks=0, good=[], bad=[1, 2])
    @example(thread=None, blanks=0, good=[], bad='text')
    @example(thread=None, blanks=0, good=[], bad=7)
    @example(thread=None, blanks=0, good=[], bad=None)
    def test_a_line_that_is_not_an_entry_object_names_its_file_and_line_number(
        self,
        tmp_path_factory: pytest.TempPathFactory,
        thread: str | None,
        blanks: int,
        good: list[Entry],
        bad: object,
    ) -> None:
        lines = ['' for _ in range(blanks)]
        lines += [entry_to_line(entry) for entry in good]
        lines.append(json.dumps(bad))

        self.expect_corrupt_line(tmp_path_factory, thread, lines, len(lines))

    @given(thread=threads, good=st.lists(entries, max_size=3), bad=not_json)
    def test_a_line_that_is_not_json_names_its_file_and_line_number(
        self,
        tmp_path_factory: pytest.TempPathFactory,
        thread: str | None,
        good: list[Entry],
        bad: str,
    ) -> None:
        lines = [*(entry_to_line(entry) for entry in good), bad]

        self.expect_corrupt_line(tmp_path_factory, thread, lines, len(lines))

    @given(content=st.binary(max_size=40))
    def test_a_case_file_that_is_not_a_case_record_raises_corrupt_case_with_its_path(
        self, tmp_path_factory: pytest.TempPathFactory, content: bytes
    ) -> None:
        repository = self.create_repository(tmp_path_factory)
        repository.case_file.write_bytes(content)

        with pytest.raises(CorruptCaseError) as raised:
            repository.read_case()

        assert raised.value.path == repository.case_file
        assert raised.value.reason
