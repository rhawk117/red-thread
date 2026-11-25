"""Scenarios for citations: resolving one when it is added and checking one later."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.errors import MisquotedCiteError, UnresolvedCiteError

from tests.casefile.ledger.builders import QUEUE_LINES, QUEUE_PATH, URL_CITE
from tests.params import as_params

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet
    from red_thread_casefile.errors import CaseFileError
    from red_thread_casefile.policy import CiteState

SLEEP_LINE = QUEUE_LINES[2].strip()
RETURN_LINE = QUEUE_LINES[3].strip()
SLEEP_CITE = f'{QUEUE_PATH}:3'


@dataclass(slots=True, kw_only=True, frozen=True)
class AddCiteCase:
    name: str
    cite: str
    quote: str | None
    error_type: type[CaseFileError] | None
    stored_quote: str | None = None
    found_at: int | None = None

    @property
    def param(self) -> ParameterSet:
        return pytest.param(self, id=self.name)


def add_cite_params() -> list[ParameterSet]:
    cases = [
        AddCiteCase(
            name='line-without-a-quote-is-captured',
            cite=SLEEP_CITE,
            quote=None,
            error_type=None,
            stored_quote=SLEEP_LINE,
        ),
        AddCiteCase(
            name='first-line-is-a-line',
            cite=f'{QUEUE_PATH}:1',
            quote=None,
            error_type=None,
            stored_quote='import time',
        ),
        AddCiteCase(
            name='last-line-is-a-line',
            cite=f'{QUEUE_PATH}:4',
            quote=None,
            error_type=None,
            stored_quote=RETURN_LINE,
        ),
        AddCiteCase(
            name='range-resolves-by-its-first-line',
            cite=f'{QUEUE_PATH}:3-4',
            quote=None,
            error_type=None,
            stored_quote=SLEEP_LINE,
        ),
        AddCiteCase(
            name='quote-on-the-cited-line-is-kept',
            cite=SLEEP_CITE,
            quote=SLEEP_LINE,
            error_type=None,
            stored_quote=SLEEP_LINE,
        ),
        AddCiteCase(
            name='quote-of-part-of-the-line-is-kept',
            cite=SLEEP_CITE,
            quote='time.sleep',
            error_type=None,
            stored_quote='time.sleep',
        ),
        AddCiteCase(
            name='line-one-past-the-end',
            cite=f'{QUEUE_PATH}:5',
            quote=None,
            error_type=UnresolvedCiteError,
        ),
        AddCiteCase(
            name='line-far-past-the-end',
            cite=f'{QUEUE_PATH}:400',
            quote=SLEEP_LINE,
            error_type=UnresolvedCiteError,
        ),
        AddCiteCase(
            name='file-that-is-not-in-the-tree',
            cite='src/gone.py:1',
            quote=None,
            error_type=UnresolvedCiteError,
        ),
        AddCiteCase(
            name='quote-found-on-another-line',
            cite=f'{QUEUE_PATH}:1',
            quote=RETURN_LINE,
            error_type=MisquotedCiteError,
            found_at=4,
        ),
        AddCiteCase(
            name='quote-found-on-the-line-before',
            cite=f'{QUEUE_PATH}:3',
            quote='def retry(job):',
            error_type=MisquotedCiteError,
            found_at=2,
        ),
        AddCiteCase(
            name='quote-found-nowhere',
            cite=f'{QUEUE_PATH}:1',
            quote='import threading',
            error_type=MisquotedCiteError,
            found_at=None,
        ),
    ]
    return as_params(cases)


def unread_cite_params() -> list[ParameterSet]:
    cites = {
        'absolute-path': '/etc/passwd:1',
        'parent-directory': '../queue.py:1',
        'parent-directory-after-a-directory': 'src/../../queue.py:1',
        'parent-directory-that-lands-inside-the-tree': 'src/../src/queue.py:3',
        'url': URL_CITE,
        'command': 'grep -n sleep src/queue.py',
    }
    return [pytest.param(cite, id=name) for name, cite in cites.items()]


@dataclass(slots=True, kw_only=True, frozen=True)
class CheckCase:
    name: str
    after: tuple[str, ...] | None
    state: CiteState
    moved_to: int | None = None

    @property
    def param(self) -> ParameterSet:
        return pytest.param(self, id=self.name)


def check_state_params() -> list[ParameterSet]:
    cases = [
        CheckCase(name='untouched', after=QUEUE_LINES, state='ok'),
        CheckCase(
            name='a-line-appended-after',
            after=(*QUEUE_LINES, 'print(1)'),
            state='ok',
        ),
        CheckCase(
            name='lines-inserted-above',
            after=('# retries', '# for jobs', *QUEUE_LINES),
            state='moved',
            moved_to=5,
        ),
        CheckCase(
            name='a-line-removed-above',
            after=QUEUE_LINES[1:],
            state='moved',
            moved_to=2,
        ),
        CheckCase(
            name='quoted-text-replaced',
            after=(*QUEUE_LINES[:2], '    await asyncio.sleep(job.delay)', QUEUE_LINES[3]),
            state='changed',
        ),
        CheckCase(
            name='quoted-text-gone-and-line-still-there',
            after=(*QUEUE_LINES[:2], '    pass', QUEUE_LINES[3]),
            state='changed',
        ),
        CheckCase(name='file-deleted', after=None, state='missing'),
        CheckCase(
            name='file-shortened-past-the-line',
            after=QUEUE_LINES[:2],
            state='missing',
        ),
    ]
    return as_params(cases)


def unchecked_cite_params() -> list[ParameterSet]:
    cites = {
        'url': URL_CITE,
        'url-with-heading': 'https://example.invalid/docs#retries',
        'command': 'grep -n sleep src/queue.py',
        'absolute-path': '/etc/passwd:1',
        'parent-directory': '../queue.py:3',
    }
    return [pytest.param(cite, id=name) for name, cite in cites.items()]
