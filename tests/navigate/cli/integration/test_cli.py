"""The navigate command line in process: verbs, exit codes and the budget on every output."""

import contextlib
import io
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from red_thread_navigate import main
from red_thread_navigate.budget import MIN_BUDGET, estimate_tokens
from red_thread_navigate.cli import PROGRAM

from tests.navigate.samples import CORE

if TYPE_CHECKING:
    from pathlib import Path

IDENTIFIER = r'[A-Za-z_][A-Za-z0-9_]{0,40}'
SUFFIXES = ('.py', '.js', '.go', '.rs', '.tf', '.txt')


@dataclass(slots=True, kw_only=True, frozen=True)
class Printed:
    code: int
    out: str
    err: str

    @property
    def everything(self) -> str:
        return self.out + self.err


def run_in(root: Path, *argv: str) -> Printed:
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.chdir(root), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return Printed(code=code, out=out.getvalue(), err=err.getvalue())


def missing_path_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('argv', [('map', 'nowhere'), ('find', 'helper', 'nowhere')])


def unknown_flag_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('flag', ['--no-cache', '--bogus'])


def empty_path_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('argv', [('map', ''), ('find', 'helper', '')])


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    tmp_path.joinpath('core.py').write_text(CORE)
    return tmp_path


class TestVerbs:
    def test_map_lists_the_symbols_with_addresses(self, repository: Path) -> None:
        printed = run_in(repository, 'map', '.')

        assert printed.code == 0
        assert 'core.py#Widget.render' in printed.out
        assert printed.err == ''

    def test_find_lists_the_definition_of_a_name(self, repository: Path) -> None:
        printed = run_in(repository, 'find', 'helper', '.')

        assert printed.code == 0
        assert 'core.py#helper' in printed.out

    def test_slice_prints_the_lines_of_a_symbol_from_the_working_directory(
        self, repository: Path
    ) -> None:
        printed = run_in(repository, 'slice', 'core.py#Widget.render')

        assert printed.code == 0
        assert 'return helper()' in printed.out

    def test_version_prints_the_package_version(self, repository: Path) -> None:
        printed = run_in(repository, '--version')

        assert (printed.code, printed.out.startswith(f'{PROGRAM} ')) == (0, True)


class TestRefusals:
    def test_a_missing_symbol_exits_one_with_the_message_on_standard_error(
        self, repository: Path
    ) -> None:
        printed = run_in(repository, 'slice', 'core.py#Missing')

        assert (printed.code, printed.out) == (1, '')
        assert 'no symbol' in printed.err
        assert 'core.py' in printed.err

    def test_an_address_outside_the_root_exits_one(self, repository: Path) -> None:
        printed = run_in(repository, 'slice', '../elsewhere.py#x')

        assert (printed.code, printed.out) == (1, '')

    @missing_path_cases()
    def test_a_missing_path_exits_one_naming_it_and_no_git_failure(
        self, repository: Path, argv: tuple[str, ...]
    ) -> None:
        printed = run_in(repository, *argv)

        assert (printed.code, printed.out) == (1, '')
        assert 'nowhere does not exist' in printed.err
        assert 'git' not in printed.err

    def test_slice_of_a_directory_says_it_is_not_a_file_and_names_map(
        self, repository: Path
    ) -> None:
        repository.joinpath('pkg').mkdir()

        printed = run_in(repository, 'slice', 'pkg#L1')

        assert (printed.code, printed.out) == (1, '')
        assert 'it is not a file' in printed.err
        assert 'Next step: map' in printed.err

    def test_a_long_refusal_is_cut_to_the_budget(self, repository: Path) -> None:
        printed = run_in(repository, '--budget', str(MIN_BUDGET), 'slice', f'{"d/" * 80}core.py#x')

        assert printed.code == 1
        assert estimate_tokens(printed.err) <= MIN_BUDGET


class TestUsage:
    @unknown_flag_cases()
    def test_an_unknown_flag_exits_two_naming_it_and_the_valid_ones(
        self, repository: Path, flag: str
    ) -> None:
        printed = run_in(repository, flag, 'map', '.')

        assert (printed.code, printed.out) == (2, '')
        assert flag in printed.err
        assert '--budget' in printed.err
        assert '--version' in printed.err

    @empty_path_cases()
    def test_an_empty_path_exits_two(self, repository: Path, argv: tuple[str, ...]) -> None:
        printed = run_in(repository, *argv)

        assert (printed.code, printed.out) == (2, '')
        assert 'PATH' in printed.err

    def test_a_budget_below_the_minimum_exits_two_naming_the_minimum(
        self, repository: Path
    ) -> None:
        printed = run_in(repository, '--budget', str(MIN_BUDGET - 1), 'map', '.')

        assert (printed.code, printed.out) == (2, '')
        assert str(MIN_BUDGET) in printed.err

    def test_a_missing_verb_exits_two(self, repository: Path) -> None:
        printed = run_in(repository)

        assert (printed.code, printed.out) == (2, '')
        assert 'map, find or slice' in printed.err


def definitions(names: list[str]) -> str:
    return '\n'.join(f'def {name}():\n    return {name}()\n' for name in names)


def contents() -> st.SearchStrategy[str]:
    names = st.lists(st.from_regex(IDENTIFIER, fullmatch=True), max_size=30)
    return st.one_of(st.text(max_size=400), names.map(definitions))


@dataclass(slots=True, kw_only=True, frozen=True)
class AddressForms:
    file_name: str

    def name_symbol(self, symbol: str) -> str:
        return f'{self.file_name}#{symbol}'

    def name_lines(self, line: int) -> str:
        return f'{self.file_name}#L{line}-L{line + 20}'

    def nest_under(self, path: str) -> str:
        return f'{path}/{self.file_name}#x'


def addresses(file_name: str) -> st.SearchStrategy[str]:
    name = st.from_regex(IDENTIFIER, fullmatch=True)
    forms = AddressForms(file_name=file_name)
    return st.one_of(
        name.map(forms.name_symbol),
        st.integers(1, 40).map(forms.name_lines),
        st.text(max_size=120),
        st.text(alphabet='abcd/.', max_size=150).map(forms.nest_under),
    )


@st.composite
def scenarios(draw: st.DrawFn) -> tuple[str, str, str, str, int]:
    file_name = f'sample{draw(st.sampled_from(SUFFIXES))}'
    name = draw(st.one_of(st.from_regex(IDENTIFIER, fullmatch=True), st.text(max_size=60)))
    budget = draw(st.one_of(st.integers(MIN_BUDGET, 300), st.just(2000)))
    return file_name, draw(contents()), name, draw(addresses(file_name)), budget


@pytest.fixture(scope='module')
def workspace(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp('property')


class TestBudgetProperty:
    @settings(deadline=None)
    @given(scenario=scenarios())
    def test_no_verb_prints_more_than_its_budget(
        self, workspace: Path, scenario: tuple[str, str, str, str, int]
    ) -> None:
        file_name, content, name, address, budget = scenario
        for stale in workspace.iterdir():
            stale.unlink()
        workspace.joinpath(file_name).write_text(content)
        commands = (
            ('map', '--', str(workspace)),
            ('find', '--', name, str(workspace)),
            ('slice', '--', address),
        )

        for command in commands:
            printed = run_in(workspace, '--budget', str(budget), *command)

            assert printed.code in {0, 1}
            assert estimate_tokens(printed.everything) <= budget, (command, printed)
