"""Scenarios for the lens outputs: part order, budgets, flags and citation forms."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from tests.casefile.ledger.builders import QUEUE_LINES, URL_CITE
from tests.casefile.ledger.memory import HEAD, NEXT_HEAD
from tests.params import as_params

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet
    from red_thread_casefile.domain import EntryKind
    from red_thread_casefile.lenses import LensName

QUEUE_CITE = 'src/queue.py:3'
QUEUE_QUOTE = 'time.sleep(job.delay)'
EDITED_LINES = (*QUEUE_LINES[:2], '    pass', QUEUE_LINES[3])
SHORTENED_LINES = QUEUE_LINES[:2]
SHIFTED_LINES = ('# header', *QUEUE_LINES)


@dataclass(slots=True, kw_only=True, frozen=True)
class LensShape:
    name: LensName
    headings: tuple[str, ...]
    budget: int
    fill_kind: EntryKind
    marks: tuple[pytest.MarkDecorator, ...] = ()


def lens_shapes() -> list[LensShape]:
    return [
        LensShape(
            name='brief',
            headings=(
                'Goal',
                'Decided',
                'Constraints',
                'Ruled out',
                'Open',
                'Pointers',
                'How to read',
            ),
            budget=60,
            fill_kind='known',
        ),
        LensShape(
            name='issue',
            headings=(
                'Summary',
                'Findings',
                'Open questions',
                'Ruled out',
                'Next steps',
                'References',
                'Pointers',
            ),
            budget=80,
            fill_kind='known',
        ),
        LensShape(
            name='handoff',
            headings=(
                'Where this stands',
                'Decided',
                'Start here',
                'Open',
                'Hypotheses',
                'Pointers',
                'How to read',
            ),
            budget=40,
            fill_kind='open',
        ),
        LensShape(
            name='report',
            headings=(
                'Summary',
                'Decided',
                'Findings',
                'Hypotheses',
                'Ruled out',
                'Open',
                'Next steps',
                'Resources',
                'Pointers',
                'How to read',
            ),
            budget=200,
            fill_kind='known',
        ),
    ]


def lens_shape_params() -> list[ParameterSet]:
    return as_params(lens_shapes())


def lens_name_params() -> list[ParameterSet]:
    return [pytest.param(shape.name, id=shape.name) for shape in lens_shapes()]


def lens_with_decisions_params() -> list[ParameterSet]:
    names = ('brief', 'handoff', 'report')
    return [pytest.param(name, id=name) for name in names]


@dataclass(slots=True, kw_only=True, frozen=True)
class FlagScenario:
    name: str
    entry_head: str | None = HEAD
    tree_head: str | None = HEAD
    tree_lines: tuple[str, ...] | None = QUEUE_LINES
    flags: tuple[str, ...] = ()
    marks: tuple[pytest.MarkDecorator, ...] = ()


def flag_scenarios() -> list[FlagScenario]:
    return [
        FlagScenario(name='current-and-intact'),
        FlagScenario(
            name='recorded-at-another-commit',
            tree_head=NEXT_HEAD,
            flags=(f'lead, recorded at {HEAD[:7]}',),
        ),
        FlagScenario(
            name='recorded-with-no-commit',
            entry_head=None,
            flags=('lead, recorded at no commit',),
        ),
        FlagScenario(
            name='tree-has-no-commit-now',
            tree_head=None,
            flags=(f'lead, recorded at {HEAD[:7]}',),
        ),
        FlagScenario(
            name='cited-line-changed', tree_lines=EDITED_LINES, flags=('citation changed',)
        ),
        FlagScenario(name='cited-file-missing', tree_lines=None, flags=('citation missing',)),
        FlagScenario(
            name='cited-line-beyond-the-file-end',
            tree_lines=SHORTENED_LINES,
            flags=('citation missing',),
        ),
        FlagScenario(
            name='cited-line-moved-down',
            tree_lines=SHIFTED_LINES,
            flags=('citation moved to line 4',),
        ),
        FlagScenario(
            name='another-commit-and-changed-line',
            tree_head=NEXT_HEAD,
            tree_lines=EDITED_LINES,
            flags=(f'lead, recorded at {HEAD[:7]}', 'citation changed'),
        ),
    ]


def flag_params() -> list[ParameterSet]:
    return as_params(flag_scenarios())


@dataclass(slots=True, kw_only=True, frozen=True)
class CiteShape:
    name: str
    cite: str
    written: str
    marks: tuple[pytest.MarkDecorator, ...] = ()


def cite_shape_params() -> list[ParameterSet]:
    shapes = [
        CiteShape(name='path-in-backticks', cite=QUEUE_CITE, written=f'`{QUEUE_CITE}`'),
        CiteShape(name='https-url-as-autolink', cite=URL_CITE, written=f'<{URL_CITE}>'),
        CiteShape(
            name='http-url-as-autolink',
            cite='http://example.invalid/docs',
            written='<http://example.invalid/docs>',
        ),
    ]
    return as_params(shapes)
