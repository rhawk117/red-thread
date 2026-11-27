"""The case directory read from Markdown: every fault named by file and line, no file written."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.errors import (
    MalformedBlockError,
    MalformedCaseError,
    MalformedFrontmatterError,
    StrayTextError,
    UndecodableFileError,
)

from tests.casefile.ledger.builders import create_case, create_finding
from tests.casefile.ledger.cases import (
    corrupt_block_params,
    corrupt_case_params,
    line_separator_params,
)
from tests.casefile.ledger.markdown import write_case_text, write_finding, write_thread_text

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_casefile.errors import CaseFileError

    from tests.casefile.ledger.cases import SeparatorCase
    from tests.casefile.ledger.directory import DirectoryHarness


def corrupt_block_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('block', corrupt_block_params())


def corrupt_case_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('text', corrupt_case_params())


def line_separator_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', line_separator_params())


def snapshot(directory: Path) -> dict[str, bytes]:
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in sorted(directory.rglob('*'))
        if path.is_file()
    }


def find_line(text: str, line: str) -> int:
    return text.split('\n').index(line) + 1


class TestDirectoryFiles:
    @pytest.fixture
    def harness(self, framed_directory_harness: DirectoryHarness) -> DirectoryHarness:
        return framed_directory_harness

    def write_block(self, harness: DirectoryHarness, block: str) -> str:
        text = f'{write_case_text(create_case())}\n### e1\n\n```yaml\n{block}\n```\n'
        harness.case_file.write_text(text, encoding='utf-8')
        return text

    def test_created_case_has_a_case_file_and_a_threads_directory(
        self, harness: DirectoryHarness
    ) -> None:
        assert harness.case_file.is_file()
        assert harness.directory.joinpath('threads').is_dir()

    def test_each_finding_is_read_from_the_file_it_was_written_in(
        self, harness: DirectoryHarness
    ) -> None:
        harness.seed(None, create_finding(finding_number=1), create_finding(finding_number=2))
        harness.seed('T1', create_finding(finding_number=1))

        finding_ids = [finding.finding_id for finding in harness.casefile.load().ledger.findings]

        assert finding_ids == ['e1', 'e2', 'T1.e1']
        assert harness.thread_file('T1').is_file()

    def test_check_leaves_every_file_byte_for_byte_as_it_was(
        self, harness: DirectoryHarness
    ) -> None:
        harness.seed(None, create_finding(finding_number=1, kind='known'))
        harness.seed('T1', create_finding(finding_number=2))
        before = snapshot(harness.directory)

        problems = harness.check().problems

        assert problems
        assert snapshot(harness.directory) == before

    @corrupt_block_cases()
    def test_a_block_that_is_not_an_finding_is_named_by_file_and_heading_line(
        self, harness: DirectoryHarness, block: str
    ) -> None:
        text = self.write_block(harness, block)

        problems: tuple[CaseFileError, ...] = harness.check().problems

        assert len(problems) == 1
        assert isinstance(problems[0], MalformedBlockError)
        assert problems[0].location.file == 'case.md'
        assert problems[0].location.line == find_line(text, '### e1')

    def test_text_outside_a_block_in_a_thread_file_names_the_thread_file(
        self, harness: DirectoryHarness
    ) -> None:
        stray = write_thread_text((create_finding(finding_number=1),)) + '\nbroken\n'
        harness.thread_file('T4').write_text(stray, encoding='utf-8')

        problems = harness.check().problems

        assert len(problems) == 1
        assert isinstance(problems[0], StrayTextError)
        assert problems[0].location.file == 'threads/T4.md'
        assert problems[0].location.line == find_line(stray, 'broken')

    def test_blank_lines_between_findings_do_not_lose_findings(
        self, harness: DirectoryHarness
    ) -> None:
        first = write_finding(create_finding(finding_number=1))
        second = write_finding(create_finding(finding_number=2))
        opening = write_case_text(create_case(), (create_finding(finding_number=1),)).removesuffix(
            first
        )
        text = f'{opening}\n\n\n{first}\n   \n\n{second}\n\n'
        harness.case_file.write_text(text, encoding='utf-8')

        assert len(harness.casefile.load().ledger.findings) == 2

    @line_separator_cases()
    def test_finding_text_with_a_unicode_line_separator_is_read_back_whole(
        self, harness: DirectoryHarness, case: SeparatorCase
    ) -> None:
        finding = create_finding(finding_number=1).replace_with(text=f'before{case.separator}after')
        harness.seed(None, finding)

        assert harness.casefile.load().ledger.findings == (finding,)

    def test_a_case_file_that_is_not_utf8_is_refused_with_its_path(
        self, harness: DirectoryHarness
    ) -> None:
        harness.case_file.write_bytes(b'---\nid: \xff\n---\n')

        with pytest.raises(UndecodableFileError) as raised:
            harness.check()

        assert raised.value.path == harness.case_file


class TestCorruptCaseFile:
    @pytest.fixture
    def harness(self, framed_directory_harness: DirectoryHarness) -> DirectoryHarness:
        return framed_directory_harness

    @corrupt_case_cases()
    def test_corrupt_frontmatter_is_reported_with_the_file_and_a_reason(
        self, harness: DirectoryHarness, text: str
    ) -> None:
        harness.case_file.write_text(text, encoding='utf-8')

        problems = harness.check().problems

        faults = [problem for problem in problems if isinstance(problem, MalformedFrontmatterError)]
        assert len(faults) == 1
        assert faults[0].file == 'case.md'
        assert faults[0].reason

    @corrupt_case_cases()
    def test_corrupt_frontmatter_is_left_as_it_was_and_the_case_will_not_load(
        self, harness: DirectoryHarness, text: str
    ) -> None:
        harness.seed('T1', create_finding(finding_number=1))
        harness.case_file.write_text(text, encoding='utf-8')

        with pytest.raises(MalformedCaseError):
            harness.casefile.load()

        assert harness.case_file.read_text(encoding='utf-8') == text
