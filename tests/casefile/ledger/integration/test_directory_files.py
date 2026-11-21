"""The directory adapter keeps files append-only and names a corrupt line by file and number."""

import json
from typing import TYPE_CHECKING

import pytest
from msgspec.structs import replace
from red_thread_casefile.errors import CorruptCaseError, CorruptLedgerError

from tests.casefile.ledger.builders import create_entry
from tests.casefile.ledger.cases import (
    VALID_LINE,
    corrupt_case_params,
    corrupt_line_params,
    line_separator_params,
)

if TYPE_CHECKING:
    from tests.casefile.ledger.cases import SeparatorCase
    from tests.casefile.ledger.directory import DirectoryHarness


def corrupt_case_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('text', corrupt_case_params())


def corrupt_line_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('line', corrupt_line_params())


def line_separator_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', line_separator_params())


class TestDirectoryFiles:
    @pytest.fixture
    def harness(self, framed_directory_harness: DirectoryHarness) -> DirectoryHarness:
        return framed_directory_harness

    def test_created_case_has_a_case_file_and_a_threads_directory(
        self, harness: DirectoryHarness
    ) -> None:
        assert harness.directory.joinpath('case.json').is_file()
        assert harness.directory.joinpath('threads').is_dir()

    def test_each_entry_is_one_line_of_its_file(self, harness: DirectoryHarness) -> None:
        harness.repository.append(None, (create_entry(seq=1), create_entry(seq=2)))
        harness.repository.append('T1', (create_entry(seq=1),))

        ledger_lines = harness.ledger_file.read_text(encoding='utf-8').splitlines()
        thread_lines = harness.thread_file('T1').read_text(encoding='utf-8').splitlines()
        assert [json.loads(line)['seq'] for line in ledger_lines] == [1, 2]
        assert [json.loads(line)['seq'] for line in thread_lines] == [1]

    def test_append_never_changes_the_bytes_already_in_the_file(
        self, harness: DirectoryHarness
    ) -> None:
        harness.repository.append(None, (create_entry(seq=1), create_entry(seq=2)))
        before = harness.ledger_file.read_bytes()

        harness.repository.append(None, (create_entry(seq=3),))

        after = harness.ledger_file.read_bytes()
        assert after.startswith(before)
        assert len(after) > len(before)
        assert after[len(before) :].count(b'\n') == 1

    def test_appending_to_a_thread_leaves_the_ledger_file_alone(
        self, harness: DirectoryHarness
    ) -> None:
        harness.repository.append(None, (create_entry(seq=1),))
        before = harness.ledger_file.read_bytes()

        harness.repository.append('T1', (create_entry(seq=1),))

        assert harness.ledger_file.read_bytes() == before

    @corrupt_line_cases()
    def test_corrupt_ledger_line_is_reported_with_its_file_and_line_number(
        self, harness: DirectoryHarness, line: str
    ) -> None:
        harness.ledger_file.write_text(f'{VALID_LINE}\n{line}\n', encoding='utf-8')

        with pytest.raises(CorruptLedgerError) as raised:
            harness.repository.read_ledger()

        assert raised.value.path == harness.ledger_file
        assert raised.value.line_number == 2
        assert f'{harness.ledger_file} line 2' in str(raised.value)

    def test_corrupt_thread_line_is_reported_with_the_thread_file(
        self, harness: DirectoryHarness
    ) -> None:
        harness.thread_file('T4').write_text('broken\n', encoding='utf-8')

        with pytest.raises(CorruptLedgerError) as raised:
            harness.repository.read_ledger()

        assert raised.value.path == harness.thread_file('T4')
        assert raised.value.line_number == 1

    def test_blank_lines_are_skipped_but_still_counted(self, harness: DirectoryHarness) -> None:
        harness.ledger_file.write_text(f'{VALID_LINE}\n\n   \nbroken\n', encoding='utf-8')

        with pytest.raises(CorruptLedgerError) as raised:
            harness.repository.read_ledger()

        assert raised.value.line_number == 4

    def test_blank_lines_between_entries_do_not_lose_entries(
        self, harness: DirectoryHarness
    ) -> None:
        harness.ledger_file.write_text(f'{VALID_LINE}\n\n{VALID_LINE}\n', encoding='utf-8')

        assert len(harness.repository.read_ledger().entries) == 2

    @line_separator_cases()
    def test_entry_text_with_a_unicode_line_separator_is_read_back_whole(
        self, harness: DirectoryHarness, case: SeparatorCase
    ) -> None:
        entry = replace(create_entry(seq=1), text=f'before{case.separator}after')
        harness.repository.append(None, (entry,))

        assert harness.repository.read_ledger().entries == (entry,)


class TestCorruptCaseFile:
    @pytest.fixture
    def harness(self, framed_directory_harness: DirectoryHarness) -> DirectoryHarness:
        return framed_directory_harness

    @corrupt_case_cases()
    def test_corrupt_case_file_is_reported_with_its_path_and_a_reason(
        self, harness: DirectoryHarness, text: str
    ) -> None:
        case_file = harness.directory.joinpath('case.json')
        case_file.write_text(text, encoding='utf-8')

        with pytest.raises(CorruptCaseError) as raised:
            harness.repository.read_case()

        assert raised.value.path == case_file
        assert raised.value.reason
        assert f'{case_file} is not a case record ({raised.value.reason})' in str(raised.value)

    @corrupt_case_cases()
    def test_corrupt_case_file_is_left_as_it_was_and_the_ledger_stays_readable(
        self, harness: DirectoryHarness, text: str
    ) -> None:
        harness.repository.append(None, (create_entry(seq=1),))
        case_file = harness.directory.joinpath('case.json')
        case_file.write_text(text, encoding='utf-8')

        with pytest.raises(CorruptCaseError):
            harness.repository.read_case()

        assert case_file.read_text(encoding='utf-8') == text
        assert len(harness.repository.read_ledger().entries) == 1
