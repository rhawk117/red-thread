"""bin/redthread-casefile from outside the plugin: a child process in a temporary git repository."""

from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.domain import PROGRAM

from tests.casefile.launcher.launcher import hostile_uv_config_params, list_tree, snapshot
from tests.casefile.ledger.builders import KNOWN
from tests.casefile.ledger.markdown import append_text

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.launcher.launcher import Launcher

OPEN = {'kind': 'open', 'text': 'what stalls the queue', 'source': 'scout'}
CASE_HOME = '.red-thread'


def hostile_uv_config_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('config', hostile_uv_config_params())


class TestCasefileScript:
    @hostile_uv_config_cases()
    def test_the_uv_config_of_the_repository_is_ignored(
        self, launcher: Launcher, config: str
    ) -> None:
        case = launcher.init()
        launcher.git.root.joinpath('uv.toml').write_text(config)
        before = snapshot(launcher.git.root)

        checked = launcher.on_case('check', case)

        assert checked.code == 0, checked.err
        assert snapshot(launcher.git.root) == before

    def test_a_case_goes_from_init_to_a_board_page_and_a_brief(self, launcher: Launcher) -> None:
        case = launcher.init()
        launcher.write(case, OPEN, KNOWN)

        rendered = launcher.on_case('render', case, '--html')
        checked = launcher.on_case('check', case)
        exported = launcher.on_case('export', case, '--lens', 'brief', '--html')

        assert [step.code for step in (rendered, checked, exported)] == [0, 0, 0]
        assert 'what stalls the queue' in rendered.out
        assert 'the sleep blocks the queue' in rendered.out
        assert case.joinpath('board.html').is_file()
        assert {path.name for path in case.joinpath('out').iterdir()} == {'brief.md', 'brief.html'}

    def test_an_unreadable_case_keeps_its_exit_code_and_its_reason(
        self, launcher: Launcher
    ) -> None:
        case = launcher.init()
        append_text(case, 'a line outside any entry\n')

        rejected = launcher.on_case('render', case)

        assert (rejected.code, rejected.out) == (1, '')
        assert f'{PROGRAM}: the case file cannot be read' in rejected.err

    def test_a_second_run_prints_nothing_on_standard_error(self, launcher: Launcher) -> None:
        case = launcher.init()

        rendered = launcher.on_case('render', case)

        assert (rendered.code, rendered.err) == (0, '')

    def test_the_plugin_is_left_as_it_was(self, launcher: Launcher) -> None:
        case = launcher.init()
        launcher.write(case, OPEN, KNOWN)

        launcher.on_case('render', case, '--html')

        assert list_tree(launcher.plugin.root) == list(launcher.plugin.files)

    def test_the_repository_gains_only_the_case_directory_and_git_ignores_it(
        self, launcher: Launcher
    ) -> None:
        before = {path.name for path in launcher.git.root.iterdir()}
        case = launcher.init()
        launcher.write(case, OPEN, KNOWN)

        launcher.on_case('render', case, '--html')

        after = {path.name for path in launcher.git.root.iterdir()}
        assert after - before == {CASE_HOME}
        assert launcher.git.run('status', '--porcelain') == ''

    def test_the_plugin_root_variable_names_where_the_package_comes_from(
        self, launcher: Launcher, tmp_path: Path
    ) -> None:
        elsewhere = tmp_path.joinpath('no-plugin-here')

        finished = launcher.run_rooted_at(elsewhere, 'render', '--case', 'any')

        assert finished.code != 0
        assert 'no-plugin-here' in finished.err
