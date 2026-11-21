"""casefile init, driven through main(argv) against a temporary git repository."""

import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.casefile.commands.cli import CliHarness

CASE_DIRECTORY = re.compile(r'created .*/\.red-thread/\d{8}-why-does-the-retry-queue\n')


class TestInit:
    def test_init_creates_the_case_and_reports_what_the_repository_offers(
        self, cli: CliHarness
    ) -> None:
        result = cli.run(
            'init',
            '--root',
            str(cli.git.root),
            '--target',
            'Why does the retry queue stall under load',
            '--kind',
            'root-cause',
            '--bar',
            'name the line',
        )

        assert result.code == 0
        assert result.err == ''
        assert CASE_DIRECTORY.match(result.out)
        assert 'languages: Python' in result.out
        assert 'navigation tool: ' in result.out

    def test_init_writes_a_case_file_that_records_the_framing_and_the_head(
        self, cli: CliHarness
    ) -> None:
        case = cli.init('retry stall', '--publish')

        record = json.loads(case.joinpath('case.json').read_text(encoding='utf-8'))
        assert record['target'] == 'retry stall'
        assert record['kind'] == 'root-cause'
        assert record['bar'] == 'name the line'
        assert record['publish'] is True
        assert record['head'] == cli.git.head

    def test_slug_names_the_case_instead_of_the_target(self, cli: CliHarness) -> None:
        case = cli.init('a long target that is not used', '--slug', 'Cache miss storm')

        assert re.fullmatch(r'\d{8}-cache-miss-storm', case.name)

    def test_init_keeps_the_case_out_of_git(self, cli: CliHarness) -> None:
        cli.init()

        assert '.red-thread/' in cli.git.root.joinpath('.git', 'info', 'exclude').read_text(
            encoding='utf-8'
        )
        assert cli.git.run('status', '--porcelain') == ''

    def test_a_second_init_of_the_same_case_is_refused(self, cli: CliHarness) -> None:
        case = cli.init()
        before = case.joinpath('case.json').read_bytes()

        result = cli.run(
            'init',
            '--root',
            str(cli.git.root),
            '--target',
            'why the retry queue stalls',
            '--kind',
            'claim',
            '--bar',
            'a different bar',
        )

        assert result.code == 1
        assert result.out == ''
        assert result.err.startswith('casefile: ')
        assert 'already exists' in result.err
        assert case.joinpath('case.json').read_bytes() == before

    def test_repeated_inits_exclude_the_directory_from_git_once(self, cli: CliHarness) -> None:
        cli.init('first case')
        cli.init('second case')
        cli.init('third case')

        lines = cli.git.root.joinpath('.git', 'info', 'exclude').read_text(encoding='utf-8')
        assert lines.splitlines().count('.red-thread/') == 1
