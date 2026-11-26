import shutil

import pytest


@pytest.fixture(scope='session')
def node() -> str:
    found = shutil.which('node')
    if found is None:
        pytest.skip('node is not installed, and the page script runs under it')
    return found
