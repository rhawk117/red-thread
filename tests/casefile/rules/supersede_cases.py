"""Scenarios for superseding entries and for numbering them."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_casefile.errors import (
    ForeignSupersededError,
    UnknownSupersededError,
)

from tests.params import as_params

if TYPE_CHECKING:
    import pytest
    from _pytest.mark import ParameterSet
    from red_thread_casefile.errors import CaseFileError


@dataclass(slots=True, kw_only=True, frozen=True)
class SupersedeCase:
    name: str
    thread: str | None
    refs: tuple[str, ...]
    error_type: type[CaseFileError] | None
    marks: tuple[pytest.MarkDecorator, ...] = ()


def list_supersede_cases() -> list[SupersedeCase]:
    return [
        SupersedeCase(
            name='primary-retires-a-case-file-entry', thread=None, refs=('e1',), error_type=None
        ),
        SupersedeCase(
            name='primary-retires-a-thread-entry', thread=None, refs=('T1.e2',), error_type=None
        ),
        SupersedeCase(
            name='primary-retires-entries-from-both-files',
            thread=None,
            refs=('e1', 'T2.e1'),
            error_type=None,
        ),
        SupersedeCase(
            name='thread-retires-its-own-entry', thread='T1', refs=('T1.e1',), error_type=None
        ),
        SupersedeCase(
            name='thread-retires-a-case-file-entry',
            thread='T1',
            refs=('e1',),
            error_type=ForeignSupersededError,
        ),
        SupersedeCase(
            name='thread-retires-another-threads-entry',
            thread='T1',
            refs=('T2.e1',),
            error_type=ForeignSupersededError,
        ),
        SupersedeCase(
            name='thread-retires-a-thread-whose-name-it-prefixes',
            thread='T1',
            refs=('T10.e1',),
            error_type=ForeignSupersededError,
        ),
        SupersedeCase(
            name='thread-retires-a-thread-whose-name-prefixes-its-own',
            thread='T10',
            refs=('T1.e1',),
            error_type=ForeignSupersededError,
        ),
        SupersedeCase(
            name='thread-retires-its-own-entry-and-a-foreign-one',
            thread='T1',
            refs=('T1.e1', 'e2'),
            error_type=ForeignSupersededError,
        ),
        SupersedeCase(
            name='unknown-case-file-ref',
            thread=None,
            refs=('e9',),
            error_type=UnknownSupersededError,
        ),
        SupersedeCase(
            name='unknown-thread-ref',
            thread=None,
            refs=('T3.e1',),
            error_type=UnknownSupersededError,
        ),
        SupersedeCase(
            name='unknown-own-ref-in-a-thread',
            thread='T1',
            refs=('T1.e9',),
            error_type=UnknownSupersededError,
        ),
        SupersedeCase(
            name='ref-that-is-no-ref',
            thread=None,
            refs=('nonsense',),
            error_type=UnknownSupersededError,
        ),
        SupersedeCase(
            name='known-ref-beside-an-unknown-one',
            thread=None,
            refs=('e1', 'e9'),
            error_type=UnknownSupersededError,
        ),
    ]


def allowed_supersede_params() -> list[ParameterSet]:
    return as_params(case for case in list_supersede_cases() if case.error_type is None)


def refused_supersede_params() -> list[ParameterSet]:
    return as_params(case for case in list_supersede_cases() if case.error_type is not None)


@dataclass(slots=True, kw_only=True, frozen=True)
class NumberingCase:
    name: str
    seqs: tuple[int, ...]
    faults: tuple[tuple[str, int], ...]
    marks: tuple[pytest.MarkDecorator, ...] = ()


def numbering_params() -> list[ParameterSet]:
    cases = [
        NumberingCase(name='in-order', seqs=(1, 2, 3), faults=()),
        NumberingCase(name='gap', seqs=(1, 2, 4), faults=(('e4', 3),)),
        NumberingCase(name='repeat', seqs=(1, 2, 2), faults=(('e2', 3),)),
        NumberingCase(name='starts-at-two', seqs=(2, 3), faults=(('e2', 1),)),
        NumberingCase(name='skips-one-then-runs-on', seqs=(1, 3, 4), faults=(('e3', 2),)),
        NumberingCase(name='swapped', seqs=(2, 1), faults=(('e2', 1), ('e1', 3))),
    ]
    return as_params(cases)
