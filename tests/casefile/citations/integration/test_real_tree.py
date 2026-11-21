"""Citations against real files: reading, resolving, and the files that must stay unread."""

from contextlib import suppress
from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.errors import BatchRejectedError

from tests.casefile.citations.cases import SLEEP_CITE, SLEEP_LINE
from tests.casefile.ledger.builders import QUEUE_LINES, QUEUE_PATH, create_valid_draft

if TYPE_CHECKING:
    from tests.casefile.ledger.directory import DirectoryHarness
    from tests.casefile.ledger.git_repository import GitRepository

OUTSIDE_TEXT = 'text of a file outside the repository'


class TestGitSourceTreeReads:
    def test_file_is_read_as_its_lines(self, git_repository: GitRepository) -> None:
        assert git_repository.tree.read_lines(QUEUE_PATH) == QUEUE_LINES

    def test_missing_file_has_no_lines(self, git_repository: GitRepository) -> None:
        assert git_repository.tree.read_lines('src/gone.py') is None

    def test_directory_has_no_lines(self, git_repository: GitRepository) -> None:
        assert git_repository.tree.read_lines('src') is None

    def test_file_that_is_not_text_is_read_without_failing(
        self, git_repository: GitRepository
    ) -> None:
        git_repository.root.joinpath('blob.bin').write_bytes(b'ok\n\xff\xfe\nend\n')

        lines = git_repository.tree.read_lines('blob.bin')

        assert lines is not None
        assert (lines[0], lines[2]) == ('ok', 'end')


class TestLineNumbering:
    def test_lines_are_numbered_the_way_an_editor_numbers_them(
        self, git_repository: GitRepository
    ) -> None:
        separators = f'a{chr(0x0C)}b{chr(0x85)}c{chr(0x2028)}d'
        git_repository.root.joinpath('odd.txt').write_text(
            f'{separators}\nsecond\n', encoding='utf-8'
        )

        assert git_repository.tree.read_lines('odd.txt') == (separators, 'second')


class TestCitesAgainstRealFiles:
    @pytest.fixture
    def harness(self, framed_directory_harness: DirectoryHarness) -> DirectoryHarness:
        return framed_directory_harness

    def cite_line_three(self, harness: DirectoryHarness) -> None:
        harness.add(replace(create_valid_draft('known'), cite=SLEEP_CITE))

    def test_cite_is_captured_from_the_file_and_checks_ok(self, harness: DirectoryHarness) -> None:
        self.cite_line_three(harness)

        [entry] = harness.repository.read_ledger().entries
        [finding] = harness.casefile.check()

        assert entry.quote == SLEEP_LINE
        assert finding.state == 'ok'

    def test_check_follows_the_file_as_it_is_edited(self, harness: DirectoryHarness) -> None:
        self.cite_line_three(harness)
        queue = harness.git.root.joinpath(QUEUE_PATH)

        queue.write_text('# a new header\n' + queue.read_text(encoding='utf-8'), encoding='utf-8')
        [moved] = harness.casefile.check()
        queue.write_text('import time\ndef retry(job):\n    pass\n', encoding='utf-8')
        [changed] = harness.casefile.check()
        queue.unlink()
        [missing] = harness.casefile.check()

        assert (moved.state, moved.moved_to) == ('moved', 4)
        assert changed.state == 'changed'
        assert missing.state == 'missing'

    def test_cite_of_a_line_past_the_end_of_the_real_file_is_rejected(
        self, harness: DirectoryHarness
    ) -> None:
        draft = replace(create_valid_draft('known'), cite=f'{QUEUE_PATH}:{len(QUEUE_LINES) + 1}')

        with pytest.raises(BatchRejectedError):
            harness.add(draft)

        assert not harness.ledger_file.exists()

    @pytest.mark.parametrize('style', ['parent', 'absolute'])
    def test_file_outside_the_repository_is_never_read(
        self, harness: DirectoryHarness, style: str
    ) -> None:
        outside = harness.git.root.parent.joinpath('outside.txt')
        outside.write_text(f'{OUTSIDE_TEXT}\n', encoding='utf-8')
        cite = f'../{outside.name}:1' if style == 'parent' else f'{outside}:1'

        with suppress(BatchRejectedError):
            harness.add(replace(create_valid_draft('known'), cite=cite))

        stored = harness.read_bytes(harness.ledger_file).decode('utf-8')
        assert OUTSIDE_TEXT not in stored
