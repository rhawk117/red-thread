"""add --file and read_input on a file that is not there: an unreadable input, never an OS error."""

import io
import string
from contextlib import redirect_stderr, redirect_stdout
from typing import TYPE_CHECKING

import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from red_thread_casefile.cli import main, read_input
from red_thread_casefile.domain import PROGRAM
from red_thread_casefile.errors import UnreadableInputError

if TYPE_CHECKING:
    from pathlib import Path


class TestMissingInputFile:
    names = st.text(alphabet=string.ascii_letters + string.digits + '-_ ', min_size=1, max_size=20)

    def locate_missing(self, factory: pytest.TempPathFactory, name: str) -> Path:
        return factory.mktemp('inputs', numbered=True).joinpath(name)

    def run_add(self, path: Path) -> tuple[int, str, str]:
        out = io.StringIO()
        err = io.StringIO()
        arguments = ['add', '--case', str(path.parent), '--round', '1', '--file', str(path)]
        with redirect_stdout(out), redirect_stderr(err):
            code = main(arguments)
        return code, out.getvalue(), err.getvalue()

    @pytest.mark.regression
    @given(name=names)
    @example(name='missing.json')
    def test_reading_a_missing_file_raises_unreadable_input_naming_the_path(
        self, tmp_path_factory: pytest.TempPathFactory, name: str
    ) -> None:
        path = self.locate_missing(tmp_path_factory, name)

        with pytest.raises(UnreadableInputError) as raised:
            read_input(str(path))

        assert raised.value.path == str(path)
        assert raised.value.reason

    @pytest.mark.regression
    @given(name=names)
    @example(name='missing.json')
    def test_add_with_a_missing_file_exits_one_and_reports_on_standard_error(
        self, tmp_path_factory: pytest.TempPathFactory, name: str
    ) -> None:
        path = self.locate_missing(tmp_path_factory, name)

        code, out, err = self.run_add(path)

        assert code == 1
        assert out == ''
        assert err.startswith(f'{PROGRAM}: ')
        assert 'cannot be read' in err
        assert str(path) in err
