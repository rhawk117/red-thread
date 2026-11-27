"""Scenarios for citations: the rules a fresh cite must meet, and the state check reports later."""

from dataclasses import dataclass
from types import NoneType
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.errors import (
    MisquotedCitationError,
    MissingQuoteError,
    UnresolvedCitationError,
)

from tests.casefile.ledger.builders import QUEUE_LINES, QUEUE_PATH, URL_CITE
from tests.params import as_params

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet
    from red_thread_casefile.policy import CitationState

SLEEP_LINE = QUEUE_LINES[2].strip()
RETURN_LINE = QUEUE_LINES[3].strip()
SLEEP_CITE = f'{QUEUE_PATH}:3'


@dataclass(slots=True, kw_only=True, frozen=True)
class CitationRuleCase:
    name: str
    citation: str
    quote: str | None
    error_type: type[object]
    found_at: int | None = None
    marks: tuple[pytest.MarkDecorator, ...] = ()


def citation_rule_params() -> list[ParameterSet]:
    cases = [
        CitationRuleCase(
            name='quote-on-the-cited-line',
            citation=SLEEP_CITE,
            quote=SLEEP_LINE,
            error_type=NoneType,
        ),
        CitationRuleCase(
            name='quote-of-part-of-the-line',
            citation=SLEEP_CITE,
            quote='time.sleep',
            error_type=NoneType,
        ),
        CitationRuleCase(
            name='first-line', citation=f'{QUEUE_PATH}:1', quote='import time', error_type=NoneType
        ),
        CitationRuleCase(
            name='last-line', citation=f'{QUEUE_PATH}:4', quote=RETURN_LINE, error_type=NoneType
        ),
        CitationRuleCase(
            name='range-is-quoted-from-its-first-line',
            citation=f'{QUEUE_PATH}:3-4',
            quote=SLEEP_LINE,
            error_type=NoneType,
        ),
        CitationRuleCase(
            name='line-without-a-quote',
            citation=SLEEP_CITE,
            quote=None,
            error_type=MissingQuoteError,
        ),
        CitationRuleCase(
            name='line-one-past-the-end',
            citation=f'{QUEUE_PATH}:5',
            quote=None,
            error_type=UnresolvedCitationError,
        ),
        CitationRuleCase(
            name='quoted-line-far-past-the-end',
            citation=f'{QUEUE_PATH}:400',
            quote=SLEEP_LINE,
            error_type=UnresolvedCitationError,
        ),
        CitationRuleCase(
            name='file-that-is-not-in-the-tree',
            citation='src/gone.py:1',
            quote=None,
            error_type=UnresolvedCitationError,
        ),
        CitationRuleCase(
            name='quote-found-on-another-line',
            citation=f'{QUEUE_PATH}:1',
            quote=RETURN_LINE,
            error_type=MisquotedCitationError,
            found_at=4,
        ),
        CitationRuleCase(
            name='quote-found-on-the-line-before',
            citation=f'{QUEUE_PATH}:3',
            quote='def retry(job):',
            error_type=MisquotedCitationError,
            found_at=2,
        ),
        CitationRuleCase(
            name='quote-found-nowhere',
            citation=f'{QUEUE_PATH}:1',
            quote='import threading',
            error_type=MisquotedCitationError,
        ),
    ]
    return as_params(cases)


def unread_citation_params() -> list[ParameterSet]:
    citations = {
        'absolute-path': '/etc/passwd:1',
        'parent-directory': '../queue.py:1',
        'parent-directory-after-a-directory': 'src/../../queue.py:1',
        'parent-directory-that-lands-inside-the-tree': 'src/../src/queue.py:3',
        'url': URL_CITE,
        'command': 'grep -n sleep src/queue.py',
    }
    return [pytest.param(citation, id=name) for name, citation in citations.items()]


@dataclass(slots=True, kw_only=True, frozen=True)
class CheckCase:
    name: str
    after: tuple[str, ...] | None
    state: CitationState
    moved_to: int | None = None
    marks: tuple[pytest.MarkDecorator, ...] = ()


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


def unchecked_citation_params() -> list[ParameterSet]:
    citations = {
        'url': URL_CITE,
        'url-with-heading': 'https://example.invalid/docs#retries',
        'command': 'grep -n sleep src/queue.py',
        'absolute-path': '/etc/passwd:1',
        'parent-directory': '../queue.py:3',
    }
    return [pytest.param(citation, id=name) for name, citation in citations.items()]
