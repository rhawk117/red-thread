"""casefile export, driven through main(argv) against a temporary git repository."""

import json
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.domain import PROGRAM

from tests.casefile.ledger.builders import KNOWN
from tests.casefile.lenses.reading import list_headings, list_refs

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.commands.cli import CliHarness

DECISION = {'kind': 'decision', 'text': 'keep the retries', 'source': 'user'}


def create_open_records(count: int) -> list[dict[str, object]]:
    return [
        {'kind': 'open', 'text': f'question {number}', 'source': 'scout'} for number in range(count)
    ]


def read_brief(case: Path) -> str:
    return case.joinpath('out', 'brief.md').read_text(encoding='utf-8')


class TestExport:
    @pytest.fixture
    def stocked(self, cli: CliHarness, case: Path) -> Path:
        cli.add(case, KNOWN, DECISION, *create_open_records(2))
        return case

    def test_export_writes_the_lens_file_in_the_case_and_reports_it(
        self, cli: CliHarness, stocked: Path
    ) -> None:
        result = cli.export(stocked, 'brief')

        assert (result.code, result.err) == (0, '')
        written = stocked.joinpath('out', 'brief.md')
        lines = result.out.splitlines()
        assert lines[0] == f'wrote {written}'
        assert lines[1].endswith(' of 60 lines')
        assert list_headings(read_brief(stocked)) == [
            'Goal',
            'Decided',
            'Constraints',
            'Open',
            'Pointers',
            'How to read',
        ]

    def test_reported_line_count_is_the_count_of_the_written_file(
        self, cli: CliHarness, stocked: Path
    ) -> None:
        result = cli.export(stocked, 'brief')

        written = sum(1 for line in read_brief(stocked).splitlines() if line.strip())
        assert result.out.splitlines()[1] == f'{written} of 60 lines'

    def test_export_with_html_writes_the_page_beside_the_markdown(
        self, cli: CliHarness, stocked: Path
    ) -> None:
        result = cli.export(stocked, 'report', '--html')

        assert result.code == 0
        assert stocked.joinpath('out', 'report.md').is_file()
        assert stocked.joinpath('out', 'report.html').is_file()
        assert result.out.splitlines()[:2] == [
            f'wrote {stocked.joinpath("out", "report.md")}',
            f'wrote {stocked.joinpath("out", "report.html")}',
        ]

    def test_export_without_html_writes_no_page(self, cli: CliHarness, stocked: Path) -> None:
        cli.export(stocked, 'brief')

        assert [path.name for path in stocked.joinpath('out').iterdir()] == ['brief.md']

    def test_a_plan_file_selects_orders_and_titles(self, cli: CliHarness, case: Path) -> None:
        cli.add(case, *create_open_records(4))
        plan = json.dumps({'title': 'Why jobs wait', 'include': ['e3', 'e1'], 'blocking': ['e1']})

        cli.export(case, 'brief', plan=plan)

        text = read_brief(case)
        assert text.splitlines()[0] == '# Why jobs wait'
        assert list_refs(text, 'Open') == ['e1', 'e3']

    def test_a_plan_on_standard_input_is_read_when_no_plan_file_is_given(
        self, cli: CliHarness, case: Path
    ) -> None:
        cli.add(case, *create_open_records(4))

        result = cli.export_from_stdin(case, 'brief', json.dumps({'include': ['e4']}))

        assert result.code == 0
        assert list_refs(read_brief(case), 'Open') == ['e4']

    def test_no_plan_exports_every_live_entry(self, cli: CliHarness, case: Path) -> None:
        cli.add(case, *create_open_records(3))

        cli.export(case, 'brief')

        assert list_refs(read_brief(case), 'Open') == ['e1', 'e2', 'e3']

    def test_a_secret_in_the_plan_is_redacted_before_it_is_written(
        self, cli: CliHarness, case: Path
    ) -> None:
        plan = json.dumps({'title': 'Leak of AKIAIOSFODNN7EXAMPLE'})

        cli.export(case, 'brief', '--html', plan=plan)

        for name in ('brief.md', 'brief.html'):
            written = case.joinpath('out', name).read_text(encoding='utf-8')
            assert 'AKIAIOSFODNN7EXAMPLE' not in written
            assert '[REDACTED:aws-key]' in written

    def test_a_retired_entry_is_not_exported(self, cli: CliHarness, case: Path) -> None:
        cli.add(case, *create_open_records(1))
        cli.add(
            case, {'kind': 'open', 'text': 'replacement', 'source': 'scout', 'supersedes': ['e1']}
        )

        cli.export(case, 'brief')

        assert list_refs(read_brief(case), 'Open') == ['e2']


class TestExportRefusals:
    @pytest.fixture
    def stocked(self, cli: CliHarness, case: Path) -> Path:
        cli.add(case, KNOWN, *create_open_records(2))
        return case

    def assert_refused_without_writing(self, cli: CliHarness, case: Path, plan: str) -> str:
        result = cli.export(case, 'brief', plan=plan)

        assert result.code == 1
        assert result.out == ''
        assert result.err.startswith(f'{PROGRAM}: ')
        assert not case.joinpath('out').exists()
        return result.err

    @pytest.mark.parametrize(
        ('plan', 'named'),
        [
            pytest.param('not json at all', 'not JSON', id='not-json'),
            pytest.param('["e1"]', 'not a JSON object', id='not-an-object'),
            pytest.param('{"mood": "calm"}', 'mood', id='unknown-key'),
            pytest.param('{"include": "e1"}', 'include', id='include-not-a-list'),
            pytest.param('{"title": 4}', 'title', id='title-not-a-string'),
        ],
    )
    def test_a_malformed_plan_is_reported_and_nothing_is_written(
        self, cli: CliHarness, stocked: Path, plan: str, named: str
    ) -> None:
        error = self.assert_refused_without_writing(cli, stocked, plan)

        assert 'the plan cannot be read' in error
        assert named in error

    def test_a_ref_that_is_not_live_is_reported_and_nothing_is_written(
        self, cli: CliHarness, stocked: Path
    ) -> None:
        error = self.assert_refused_without_writing(cli, stocked, '{"include": ["e9"]}')

        assert 'e9' in error

    def test_a_retired_ref_is_reported_and_nothing_is_written(
        self, cli: CliHarness, stocked: Path
    ) -> None:
        cli.add(stocked, {'kind': 'open', 'text': 'new', 'source': 'scout', 'supersedes': ['e2']})

        error = self.assert_refused_without_writing(cli, stocked, '{"blocking": ["e2"]}')

        assert 'e2' in error

    def test_an_output_over_budget_names_the_figures_and_leaves_the_earlier_file_alone(
        self, cli: CliHarness, stocked: Path
    ) -> None:
        cli.export(stocked, 'brief')
        earlier = stocked.joinpath('out', 'brief.md').read_bytes()
        cli.add(stocked, *create_open_records(70))

        result = cli.export(stocked, 'brief', '--html')

        assert result.code == 1
        assert result.out == ''
        assert 'brief' in result.err
        assert 'budget is 60' in result.err
        assert stocked.joinpath('out', 'brief.md').read_bytes() == earlier
        assert not stocked.joinpath('out', 'brief.html').exists()

    def test_the_same_ledger_fits_the_report_budget(self, cli: CliHarness, stocked: Path) -> None:
        cli.add(stocked, *create_open_records(70))

        result = cli.export(stocked, 'report')

        assert result.code == 0
        assert result.out.splitlines()[-1].endswith(' of 200 lines')

    def test_a_directory_that_is_not_a_case_is_an_error(self, cli: CliHarness) -> None:
        result = cli.export(cli.git.root.joinpath('.red-thread', 'nothing-here'), 'brief')

        assert result.code == 1
        assert result.err.startswith(f'{PROGRAM}: ')
