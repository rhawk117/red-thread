"""scripts/navigate.sh from outside the plugin: a child process in a fixture repository."""

import shutil
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from tests.casefile.launcher.children import ChildRunner
from tests.casefile.launcher.launcher import (
    copy_plugin,
    hostile_uv_config_params,
    read_outside_environment,
    snapshot,
)

if TYPE_CHECKING:
    from pathlib import Path

    from tests.casefile.launcher.children import Finished

CORE = """\
def helper():
    return 1


class Widget:
    def render(self):
        return helper()
"""
CLIENT = """\
from core import helper


def use():
    return helper() + helper()
"""


@dataclass(slots=True, kw_only=True, frozen=True)
class Navigator:
    script: Path
    repository: Path

    def run(self, *arguments: str) -> Finished:
        runner = ChildRunner(cwd=self.repository, env=read_outside_environment())
        return runner.run('sh', str(self.script), *arguments)


@pytest.fixture(scope='session')
def navigate_script(pytestconfig: pytest.Config, tmp_path_factory: pytest.TempPathFactory) -> Path:
    source = pytestconfig.rootpath
    copy = copy_plugin(source, tmp_path_factory.mktemp('plugin'))
    skipped = shutil.ignore_patterns('__pycache__', '*.pyc', '*.egg-info', '.venv')
    shutil.copytree(
        source.joinpath('packages', 'navigate'),
        copy.root.joinpath('packages', 'navigate'),
        ignore=skipped,
    )
    shutil.copy2(source.joinpath('scripts', 'navigate.sh'), copy.root.joinpath('scripts'))
    return copy.root.joinpath('scripts', 'navigate.sh')


@pytest.fixture
def navigator(navigate_script: Path, tmp_path: Path) -> Navigator:
    repository = tmp_path.joinpath('fixture')
    repository.mkdir()
    repository.joinpath('core.py').write_text(CORE)
    repository.joinpath('client.py').write_text(CLIENT)
    return Navigator(script=navigate_script, repository=repository)


def hostile_uv_config_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('config', hostile_uv_config_params())


class TestNavigateScript:
    @hostile_uv_config_cases()
    def test_the_uv_config_of_the_repository_is_ignored(
        self, navigator: Navigator, config: str
    ) -> None:
        navigator.repository.joinpath('uv.toml').write_text(config)
        before = snapshot(navigator.repository)

        mapped = navigator.run('map', '.')

        assert (mapped.code, 'core.py#Widget.render' in mapped.out) == (0, True)
        assert snapshot(navigator.repository) == before

    def test_map_find_and_slice_print_their_addresses_and_leave_the_repository_alone(
        self, navigator: Navigator
    ) -> None:
        before = snapshot(navigator.repository)

        mapped = navigator.run('map', '.')
        found = navigator.run('find', 'helper', '.')
        sliced = navigator.run('slice', 'core.py#Widget.render')

        assert [step.code for step in (mapped, found, sliced)] == [0, 0, 0]
        assert 'core.py#Widget.render' in mapped.out
        assert 'core.py#helper' in found.out
        assert 'client.py' in found.out
        assert 'core.py#Widget.render' in sliced.out
        assert '6:     def render(self):' in sliced.out
        assert '7:         return helper()' in sliced.out
        assert snapshot(navigator.repository) == before

    def test_an_unknown_flag_exits_two_naming_it_and_the_valid_flags(
        self, navigator: Navigator
    ) -> None:
        finished = navigator.run('--no-cache', 'map', '.')

        assert (finished.code, finished.out) == (2, '')
        assert '--no-cache' in finished.err
        assert '--budget' in finished.err

    def test_a_budget_below_the_minimum_exits_two_naming_the_minimum(
        self, navigator: Navigator
    ) -> None:
        finished = navigator.run('--budget', '5', 'map', '.')

        assert (finished.code, finished.out) == (2, '')
        assert 'minimum of 32' in finished.err

    def test_a_refusal_exits_one_on_standard_error(self, navigator: Navigator) -> None:
        finished = navigator.run('slice', 'core.py#Missing')

        assert (finished.code, finished.out) == (1, '')
        assert 'no symbol' in finished.err
