"""Scenarios for superseding entries and for stamping sequence numbers."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.errors import (
    ForeignSupersededError,
    UnknownSupersededError,
)

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet
    from red_thread_casefile.errors import CaseFileError


@dataclass(slots=True, kw_only=True, frozen=True)
class SupersedeCase:
    name: str
    thread: str | None
    refs: tuple[str, ...]
    error_type: type[CaseFileError] | None

    @property
    def param(self) -> ParameterSet:
        return pytest.param(self, id=self.name)


def supersede_params() -> list[ParameterSet]:
    cases = [
        SupersedeCase(
            name='primary-retires-a-ledger-entry', thread=None, refs=('e1',), error_type=None
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
            name='thread-retires-a-ledger-entry',
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
            name='unknown-ledger-ref', thread=None, refs=('e9',), error_type=UnknownSupersededError
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
    return [case.param for case in cases]


@dataclass(slots=True, kw_only=True, frozen=True)
class SeqCase:
    name: str
    thread: str | None
    count: int
    refs: tuple[str, ...]

    @property
    def param(self) -> ParameterSet:
        return pytest.param(self, id=self.name)


def seq_params() -> list[ParameterSet]:
    cases = [
        SeqCase(name='ledger-continues-after-its-own-entries', thread=None, count=1, refs=('e3',)),
        SeqCase(
            name='ledger-batch-numbers-consecutively', thread=None, count=3, refs=('e3', 'e4', 'e5')
        ),
        SeqCase(
            name='thread-continues-after-its-own-entries',
            thread='T1',
            count=2,
            refs=('T1.e3', 'T1.e4'),
        ),
        SeqCase(name='new-thread-starts-at-one', thread='T2', count=2, refs=('T2.e1', 'T2.e2')),
        SeqCase(name='thread-ten-starts-at-one', thread='T10', count=1, refs=('T10.e1',)),
    ]
    return [case.param for case in cases]
