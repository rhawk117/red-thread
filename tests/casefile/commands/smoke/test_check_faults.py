"""casefile check on entries written by hand: each fault named at its file and line."""

from typing import TYPE_CHECKING

from red_thread_casefile.domain import CASE_FILE, PROGRAM

from tests.casefile.entries.blocks import ROUND, write_block_entry
from tests.casefile.ledger.builders import KNOWN
from tests.casefile.ledger.markdown import append_text
from tests.casefile.redaction.cases import LEAKED
from tests.casefile.rules.places import place_entry

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.commands.cli import CliHarness

OPEN = {'kind': 'open', 'text': 'what stalls the queue', 'source': 'scout'}


def snapshot(case: Path) -> dict[str, bytes]:
    return {path.relative_to(case).as_posix(): path.read_bytes() for path in case.rglob('*.md')}


class TestCheckPasses:
    def test_entries_written_by_hand_pass_and_their_citations_are_counted(
        self, cli: CliHarness, case: Path
    ) -> None:
        cli.write(case, OPEN, KNOWN)
        cli.write(case, OPEN, thread='T1')

        result = cli.check(case)

        assert (result.code, result.err) == (0, '')
        assert result.out.splitlines()[0] == (
            'checked 1 citations: 1 ok, 0 moved, 0 changed, 0 missing, 0 unchecked'
        )

    def test_check_changes_no_file_even_when_it_finds_faults(
        self, cli: CliHarness, case: Path
    ) -> None:
        cli.write(
            case, {**OPEN, 'text': f'the key {LEAKED} is in the log'}, {**KNOWN, 'quote': None}
        )
        before = snapshot(case)

        result = cli.check(case)

        assert result.code == 1
        assert snapshot(case) == before


class TestCheckFaults:
    def read_case_text(self, case: Path) -> str:
        return case.joinpath(CASE_FILE).read_text(encoding='utf-8')

    def test_every_faulty_entry_is_listed_at_its_file_and_line(
        self, cli: CliHarness, case: Path
    ) -> None:
        uncited = {**KNOWN, 'cite': None, 'quote': None}
        shape = {**OPEN, 'kind': 'finding'}
        decision = {'kind': 'decision', 'text': 'use a queue', 'source': 'scout'}
        cli.write(case, OPEN, uncited, shape, decision)
        text = self.read_case_text(case)

        result = cli.check(case)

        assert result.code == 1
        assert result.err == ''
        assert result.out.startswith('3 faults; check changed no file:')
        assert all(place_entry(text, None, seq) in result.out for seq in (2, 3, 4))
        assert place_entry(text, None, 1) not in result.out

    def test_a_thread_entry_is_named_in_its_thread_file(self, cli: CliHarness, case: Path) -> None:
        cli.write(case, {**OPEN, 'kind': 'finding'}, thread='T1')
        text = case.joinpath('threads', 'T1.md').read_text(encoding='utf-8')

        result = cli.check(case)

        assert result.code == 1
        assert place_entry(text, 'T1', 1) in result.out

    def test_a_file_in_threads_that_is_not_a_thread_is_named(
        self, cli: CliHarness, case: Path
    ) -> None:
        case.joinpath('threads', 'notes.md').write_text('# notes\n', encoding='utf-8')

        result = cli.check(case)

        assert result.code == 1
        assert 'threads/notes.md is not a thread file' in result.out

    def test_a_block_that_is_not_yaml_is_a_fault_not_a_traceback(
        self, cli: CliHarness, case: Path
    ) -> None:
        append_text(case, f'{ROUND}\n{write_block_entry(1, "kind: open\n\ttext: a\n")}')

        result = cli.check(case)

        assert result.code == 1
        assert result.err == ''
        assert 'e1: the yaml block cannot be read' in result.out

    def test_a_secret_is_named_with_the_scrubbed_text_to_write_instead(
        self, cli: CliHarness, case: Path
    ) -> None:
        cli.write(case, {**OPEN, 'text': f'the key {LEAKED} is in the log'})

        result = cli.check(case)

        assert result.code == 1
        assert '[REDACTED:aws-key]' in result.out
        assert LEAKED not in result.out
        assert LEAKED in self.read_case_text(case)

    def test_a_cite_without_a_quote_names_the_line_to_quote(
        self, cli: CliHarness, case: Path
    ) -> None:
        cli.write(case, {**KNOWN, 'quote': None})

        result = cli.check(case)

        assert result.code == 1
        assert 'which reads: time.sleep(job.delay)' in result.out

    def test_a_quote_found_on_another_line_names_that_line(
        self, cli: CliHarness, case: Path
    ) -> None:
        cli.write(case, {**KNOWN, 'cite': 'src/queue.py:1', 'quote': 'return job.run()'})

        result = cli.check(case)

        assert result.code == 1
        assert 'The quoted text is at line 4' in result.out

    def test_a_cite_of_a_missing_line_does_not_resolve(self, cli: CliHarness, case: Path) -> None:
        cli.write(case, {**KNOWN, 'cite': 'src/queue.py:99'})

        result = cli.check(case)

        assert result.code == 1
        assert 'src/queue.py:99 does not resolve' in result.out

    def test_a_directory_that_is_not_a_case_is_an_error(self, cli: CliHarness) -> None:
        result = cli.check(cli.git.root.joinpath('.red-thread', 'nothing-here'))

        assert result.code == 1
        assert result.err.startswith(f'{PROGRAM}: ')
        assert 'no case.md' in result.err
