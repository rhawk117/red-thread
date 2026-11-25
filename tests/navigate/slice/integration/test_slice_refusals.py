"""Slicing refusals: what each says, how it ends and which next step it names."""

from typing import TYPE_CHECKING

import pytest
from red_thread_navigate.address import AddressError
from red_thread_navigate.budget import MIN_BUDGET, estimate_tokens
from red_thread_navigate.slice import SliceError
from red_thread_navigate.slice.policy import OUTSIDE_ROOT_HINT

from tests.navigate.samples import BIG_BUDGET, CORE, NAVIGATOR
from tests.navigate.symbols.samples import SourceDir

if TYPE_CHECKING:
    from pathlib import Path

LONG_DIRS = '/'.join(f'directory{number}' for number in range(14))


def hint_cases() -> list[tuple[str, str]]:
    return [
        ('a.py#zzzzzz', 'Next step: map a.py to see the names there.'),
        ('a.py#L50', 'Next step: slice a.py#L1-L7.'),
        ('link.py#L1', f'Next step: {OUTSIDE_ROOT_HINT}.'),
        ('pkg#L1', 'Next step: map pkg to see the names there.'),
        ('../x.py#L1', f'Next step: {OUTSIDE_ROOT_HINT}.'),
    ]


def hint_set_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(('address', 'tail'), hint_cases())


def short_hint_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(('address', 'tail'), hint_cases()[:4])


def long_path_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('address', ['a.py#zzzzzz', 'a.py#L50', 'link.py#L1', 'pkg#L1'])


@pytest.fixture
def source(tmp_path: Path) -> SourceDir:
    return SourceDir(root=tmp_path)


def refusal_message(address: str, *, root: Path, budget: int) -> str:
    with pytest.raises((SliceError, AddressError)) as raised:
        NAVIGATOR.slice(address, root=root, budget=budget)
    return str(raised.value)


class TestRefusalContent:
    @pytest.fixture
    def short(self, source: SourceDir) -> SourceDir:
        source.write('core.py', CORE)
        return source

    @pytest.fixture
    def empty(self, source: SourceDir) -> SourceDir:
        source.write('empty.py', '')
        return source

    @pytest.fixture
    def linked(self, tmp_path: Path) -> SourceDir:
        root = SourceDir(root=tmp_path / 'root')
        root.write('placeholder.py', '')
        outside = SourceDir(root=tmp_path).write('secret.py', CORE)
        root.root.joinpath('link.py').symlink_to(outside)
        return root

    def test_unknown_symbol_is_refused_with_the_nearest_names(self, short: SourceDir) -> None:
        with pytest.raises(SliceError, match=r'nearest names: .*helper'):
            NAVIGATOR.slice('core.py#helpr', root=short.root, budget=BIG_BUDGET)

    def test_unknown_symbol_with_no_similar_name_names_map_as_the_next_step(
        self, short: SourceDir
    ) -> None:
        message = refusal_message('core.py#zzzzzz', root=short.root, budget=BIG_BUDGET)

        assert message.endswith('Next step: map core.py to see the names there.')

    def test_lines_past_the_end_are_refused(self, short: SourceDir) -> None:
        with pytest.raises(SliceError, match='past its end'):
            NAVIGATOR.slice('core.py#L50', root=short.root, budget=BIG_BUDGET)

    def test_the_first_line_of_an_empty_file_is_past_its_end(self, empty: SourceDir) -> None:
        message = refusal_message('empty.py#L1', root=empty.root, budget=BIG_BUDGET)

        assert message.startswith('empty.py has 0 lines, so L1 is past its end')

    def test_symlink_leaving_the_root_is_refused(self, linked: SourceDir) -> None:
        with pytest.raises(SliceError, match='outside the root'):
            NAVIGATOR.slice('link.py#L1-L2', root=linked.root, budget=BIG_BUDGET)

    def test_address_outside_the_root_is_refused(self, short: SourceDir) -> None:
        with pytest.raises(AddressError):
            NAVIGATOR.slice('../x.py#L1', root=short.root, budget=BIG_BUDGET)


class TestNextStep:
    @pytest.fixture
    def hinted(self, tmp_path: Path) -> Path:
        root = SourceDir(root=tmp_path / 'r')
        root.write('a.py', CORE)
        root.write('pkg/inner.py', CORE)
        outside = SourceDir(root=tmp_path).write('secret.py', CORE)
        root.root.joinpath('link.py').symlink_to(outside)
        return root.root

    @hint_set_cases()
    def test_each_refusal_ends_with_a_next_step_at_a_large_budget(
        self, hinted: Path, address: str, tail: str
    ) -> None:
        message = refusal_message(address, root=hinted, budget=BIG_BUDGET)

        assert message.endswith(tail)

    @short_hint_cases()
    def test_a_short_refusal_keeps_its_next_step_at_the_minimum_budget(
        self, hinted: Path, address: str, tail: str
    ) -> None:
        message = refusal_message(address, root=hinted, budget=MIN_BUDGET)

        assert message.endswith(tail)
        assert estimate_tokens(message) <= MIN_BUDGET

    @hint_set_cases()
    def test_the_next_step_is_dropped_where_it_does_not_fit_and_the_refusal_still_fits(
        self, hinted: Path, address: str, tail: str
    ) -> None:
        full = refusal_message(address, root=hinted, budget=BIG_BUDGET)
        budget = estimate_tokens(full) - 1

        message = refusal_message(address, root=hinted, budget=budget)

        assert 'Next step' not in message
        assert estimate_tokens(message) <= budget
        assert full.removesuffix(tail).rstrip('. ') in message

    @long_path_cases()
    def test_a_long_path_refusal_still_fits_the_minimum_budget(
        self, hinted: Path, address: str
    ) -> None:
        message = refusal_message(f'{LONG_DIRS}/../{address}', root=hinted, budget=MIN_BUDGET)

        assert estimate_tokens(message) <= MIN_BUDGET
