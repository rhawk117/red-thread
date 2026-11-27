"""Only the commands that draw a page load jinja2: importing the command line does not."""

import sys
from typing import TYPE_CHECKING

from tests.casefile.launcher.children import ChildRunner

if TYPE_CHECKING:
    from pathlib import Path

PROBE = "import sys, red_thread_casefile.cli; print('jinja2' in sys.modules)"


def test_the_command_line_imports_without_jinja2(tmp_path: Path) -> None:
    finished = ChildRunner(cwd=tmp_path).run(sys.executable, '-c', PROBE)

    assert finished.code == 0, finished.err
    assert finished.out.strip() == 'False'
