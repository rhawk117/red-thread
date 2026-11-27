"""Frontmatter: the fenced split of a file's lines and the YAML decode of its header."""

import msgspec
import pytest
from red_thread_core.frontmatter import (
    FenceReasons,
    FrontSplit,
    decode_yaml,
    find_closing,
    split_frontmatter,
)


class Header(msgspec.Struct, frozen=True, kw_only=True):
    title: str


def opening_problem_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        'lines',
        [
            pytest.param((), id='empty'),
            pytest.param(('title: a', '---', '# body'), id='first-line-not-a-fence'),
        ],
    )


class TestSplitFrontmatter:
    lines = ('---', 'title: a', '---', '# body')

    def test_a_valid_file_splits_into_its_front_and_closing_index(self) -> None:
        assert split_frontmatter(self.lines) == FrontSplit(front=('title: a',), closing=2)

    @opening_problem_cases()
    def test_missing_opening_fence_is_no_opening(self, lines: tuple[str, ...]) -> None:
        assert split_frontmatter(lines) == 'no_opening'

    def test_missing_closing_fence_is_no_closing(self) -> None:
        assert split_frontmatter(('---', 'title: a', '# body')) == 'no_closing'

    def test_find_closing_ignores_the_first_line(self) -> None:
        assert find_closing(('---', 'x')) is None

    def test_find_closing_finds_the_fence_after_the_first_line(self) -> None:
        assert find_closing(('---', 'x', '---')) == 2


class TestFenceReasons:
    def test_each_fence_problem_maps_to_its_own_reason(self) -> None:
        reasons = FenceReasons(no_opening='no opening fence', no_closing='no closing fence')

        assert reasons.explain('no_opening') == 'no opening fence'
        assert reasons.explain('no_closing') == 'no closing fence'


class TestDecodeYaml:
    def test_valid_yaml_returns_the_decoded_value(self) -> None:
        assert decode_yaml('title: a', Header) == Header(title='a')

    def test_bad_yaml_returns_a_decode_error(self) -> None:
        assert isinstance(decode_yaml('title: [', Header), msgspec.DecodeError)
