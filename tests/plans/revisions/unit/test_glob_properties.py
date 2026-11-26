"""find_shared_path agrees with full_match: a witness exactly when some path matches both globs."""

from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import pytest
from hypothesis import example, given
from red_thread_plans.util import find_shared_path

from tests.plans.revisions.strategies import (
    glob_modes,
    glob_path,
    matches_owned,
    owned_globs,
    paths,
)

if TYPE_CHECKING:
    from tests.plans.revisions.strategies import GlobMode

DOT_NAMES = frozenset({'.', '..'})


def is_plain_path(path: str) -> bool:
    parts = path.split('/')
    return all(parts) and not DOT_NAMES.intersection(parts)


@given(left=owned_globs, right=owned_globs)
@example(left='*.py', right='src/**')
@example(left='src/**', right='src/core/*.py')
@example(left='*', right='.*')
@example(left='a/**', right='a')
def test_a_shared_path_matches_both_globs_and_is_a_plain_path(left: str, right: str) -> None:
    shared = find_shared_path(left, right)

    assert shared is None or matches_owned(shared, left)
    assert shared is None or matches_owned(shared, right)
    assert shared is None or is_plain_path(shared)


@given(path=paths, left=owned_globs, right=owned_globs)
def test_a_path_both_globs_match_means_a_shared_path_is_found(
    path: str, left: str, right: str
) -> None:
    both = matches_owned(path, left) and matches_owned(path, right)

    assert not both or find_shared_path(left, right) is not None


@pytest.mark.regression
@given(path=paths, left_modes=glob_modes, right_modes=glob_modes)
@example(path='a/b', left_modes=['dir'] * 4, right_modes=['keep', 'star', 'keep', 'keep'])
@example(path='.a', left_modes=['star'] * 4, right_modes=['any'] * 4)
@example(path='a', left_modes=['skip'] * 4, right_modes=['deep'] * 4)
def test_two_globs_cut_from_one_path_share_a_path(
    path: str, left_modes: list[GlobMode], right_modes: list[GlobMode]
) -> None:
    left = glob_path(path, left_modes)
    right = glob_path(path, right_modes)

    assert matches_owned(path, left)
    assert matches_owned(path, right)
    assert find_shared_path(left, right) is not None


@given(left=owned_globs, right=owned_globs)
def test_sharing_a_path_is_symmetric(left: str, right: str) -> None:
    assert (find_shared_path(left, right) is None) == (find_shared_path(right, left) is None)


@given(path=paths)
def test_a_literal_path_shares_only_itself(path: str) -> None:
    assert find_shared_path(path, path) == PurePosixPath(path).as_posix()
