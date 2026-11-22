"""The launcher, run from a copy of the plugin so that a write into the plugin would show."""

from typing import TYPE_CHECKING

import pytest

from tests.casefile.launcher.launcher import Launcher, copy_plugin, read_outside_environment

if TYPE_CHECKING:
    from tests.casefile.launcher.launcher import PluginCopy
    from tests.casefile.ledger.git_repository import GitRepository


@pytest.fixture(scope='session')
def plugin_copy(
    pytestconfig: pytest.Config, tmp_path_factory: pytest.TempPathFactory
) -> PluginCopy:
    return copy_plugin(pytestconfig.rootpath, tmp_path_factory.mktemp('plugin'))


@pytest.fixture
def launcher(plugin_copy: PluginCopy, git_repository: GitRepository) -> Launcher:
    return Launcher(plugin=plugin_copy, git=git_repository, environment=read_outside_environment())
