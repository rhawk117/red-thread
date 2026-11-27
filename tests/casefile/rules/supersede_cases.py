"""Scenarios for superseding findings and for numbering them."""

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
    finding_ids: tuple[str, ...]
    error_type: type[CaseFileError] | None
    marks: tuple[pytest.MarkDecorator, ...] = ()


def list_supersede_cases() -> list[SupersedeCase]:
    return [
        SupersedeCase(
            name='primary-retires-a-case-file-finding',
            thread=None,
            finding_ids=('e1',),
            error_type=None,
        ),
        SupersedeCase(
            name='primary-retires-a-thread-finding',
            thread=None,
            finding_ids=('T1.e2',),
            error_type=None,
        ),
        SupersedeCase(
            name='primary-retires-findings-from-both-files',
            thread=None,
            finding_ids=('e1', 'T2.e1'),
            error_type=None,
        ),
        SupersedeCase(
            name='thread-retires-its-own-finding',
            thread='T1',
            finding_ids=('T1.e1',),
            error_type=None,
        ),
        SupersedeCase(
            name='thread-retires-a-case-file-finding',
            thread='T1',
            finding_ids=('e1',),
            error_type=ForeignSupersededError,
        ),
        SupersedeCase(
            name='thread-retires-another-threads-finding',
            thread='T1',
            finding_ids=('T2.e1',),
            error_type=ForeignSupersededError,
        ),
        SupersedeCase(
            name='thread-retires-a-thread-whose-name-it-prefixes',
            thread='T1',
            finding_ids=('T10.e1',),
            error_type=ForeignSupersededError,
        ),
        SupersedeCase(
            name='thread-retires-a-thread-whose-name-prefixes-its-own',
            thread='T10',
            finding_ids=('T1.e1',),
            error_type=ForeignSupersededError,
        ),
        SupersedeCase(
            name='thread-retires-its-own-finding-and-a-foreign-one',
            thread='T1',
            finding_ids=('T1.e1', 'e2'),
            error_type=ForeignSupersededError,
        ),
        SupersedeCase(
            name='unknown-case-file-finding-id',
            thread=None,
            finding_ids=('e9',),
            error_type=UnknownSupersededError,
        ),
        SupersedeCase(
            name='unknown-thread-finding-id',
            thread=None,
            finding_ids=('T3.e1',),
            error_type=UnknownSupersededError,
        ),
        SupersedeCase(
            name='unknown-own-finding-id-in-a-thread',
            thread='T1',
            finding_ids=('T1.e9',),
            error_type=UnknownSupersededError,
        ),
        SupersedeCase(
            name='finding-id-that-is-no-finding-id',
            thread=None,
            finding_ids=('nonsense',),
            error_type=UnknownSupersededError,
        ),
        SupersedeCase(
            name='known-finding-id-beside-an-unknown-one',
            thread=None,
            finding_ids=('e1', 'e9'),
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
