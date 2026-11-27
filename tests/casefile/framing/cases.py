"""Scenarios for case ids and for the languages a case records."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from tests.core.timekeeping.clock import MOMENT
from tests.params import as_params

if TYPE_CHECKING:
    import pytest
    from _pytest.mark import ParameterSet


@dataclass(slots=True, kw_only=True, frozen=True)
class CaseIdCase:
    name: str
    created: datetime
    label: str
    expected: str
    marks: tuple[pytest.MarkDecorator, ...] = ()


def case_id_params() -> list[ParameterSet]:
    cases = [
        CaseIdCase(
            name='date-and-slug',
            created=MOMENT,
            label='retry queue slowdown',
            expected='20261121-retry-queue-slowdown',
        ),
        CaseIdCase(
            name='exactly-five-words',
            created=MOMENT,
            label='one two three four five',
            expected='20261121-one-two-three-four-five',
        ),
        CaseIdCase(
            name='six-words-keep-five',
            created=MOMENT,
            label='one two three four five six',
            expected='20261121-one-two-three-four-five',
        ),
        CaseIdCase(
            name='long-sentence-keeps-the-first-five',
            created=MOMENT,
            label='Retry queue slowdown in the worker pool after deploy',
            expected='20261121-retry-queue-slowdown-in-the',
        ),
        CaseIdCase(
            name='case-and-punctuation-are-flattened',
            created=MOMENT,
            label='Why does Retry-Queue stall?!',
            expected='20261121-why-does-retry-queue-stall',
        ),
        CaseIdCase(
            name='utc-date-is-taken-from-the-timestamp',
            created=datetime(2026, 12, 31, 23, 59, 59, tzinfo=UTC),
            label='year end',
            expected='20261231-year-end',
        ),
        CaseIdCase(
            name='single-word',
            created=MOMENT,
            label='latency',
            expected='20261121-latency',
        ),
    ]
    return as_params(cases)


@dataclass(slots=True, kw_only=True, frozen=True)
class LanguageCase:
    name: str
    files: tuple[str, ...]
    languages: tuple[str, ...]
    marks: tuple[pytest.MarkDecorator, ...] = ()


def count_files(**counts: int) -> tuple[str, ...]:
    return tuple(
        f'f{number}.{suffix}' for suffix, count in counts.items() for number in range(count)
    )


def language_params() -> list[ParameterSet]:
    cases = [
        LanguageCase(name='no-files', files=(), languages=()),
        LanguageCase(name='no-known-language', files=('README.md', 'data.csv'), languages=()),
        LanguageCase(
            name='most-files-first',
            files=('a.go', 'b.py', 'c.py', 'd.py', 'e.go', 'f.rs'),
            languages=('Python', 'Go', 'Rust'),
        ),
        LanguageCase(
            name='suffixes-of-one-language-are-merged',
            files=('a.ts', 'b.tsx', 'c.js', 'd.ts'),
            languages=('TypeScript', 'JavaScript'),
        ),
        LanguageCase(
            name='nested-paths-and-uppercase-suffixes',
            files=('src/deep/a.PY', 'src/b.py', 'docs/c.md'),
            languages=('Python',),
        ),
        LanguageCase(
            name='at-most-five-languages',
            files=count_files(py=7, go=6, rs=5, rb=4, java=3, kt=2, zig=1),
            languages=('Python', 'Go', 'Rust', 'Ruby', 'Java'),
        ),
    ]
    return as_params(cases)
