"""Strategies for the values most casefile properties generate: text, entries, cases and refs.

entries and cases hold only what a case file can carry: a day and a short head from a round
heading, text with something in it, and a frontmatter that git and the clock could have written.
"""

from datetime import UTC, date, datetime

from hypothesis import strategies as st
from red_thread_casefile.domain import (
    CASE_KINDS,
    ENTRY_KINDS,
    VERDICTS,
    Capabilities,
    Case,
    Entry,
)

from tests.casefile.ledger.memory import MOMENT

LINE_BREAKERS = '\x0b\x0c\x1c\x1d\x1e\x85\N{LINE SEPARATOR}\N{PARAGRAPH SEPARATOR}'
POOLED_THREADS = (None, 'T1', 'T2', 'T10')
POOLED_REFS = ('e1', 'e2', 'e3', 'T1.e1', 'T1.e2', 'T1.e3', 'T2.e1', 'T10.e1', 'T10.e2')


def optional[Value](strategy: st.SearchStrategy[Value]) -> st.SearchStrategy[Value | None]:
    return st.one_of(st.none(), strategy)


words = st.text(alphabet=st.characters(categories=('L', 'N', 'P', 'S')), min_size=1, max_size=20)
free_text = st.one_of(
    st.text(max_size=40),
    st.text(alphabet=LINE_BREAKERS + '\n\r\t "\\ab', max_size=40),
)
filled_text = free_text.filter(str.strip)
days = st.dates().map(date.isoformat)
short_heads = st.from_regex(r'[0-9a-f]{7}', fullmatch=True)
full_heads = st.from_regex(r'[0-9a-f]{40}', fullmatch=True)
moments = st.datetimes(timezones=st.just(UTC)).map(datetime.isoformat)
thread_names = st.sampled_from(('T1', 'T2', 'T3', 'T10', 'T11'))
entry_kinds = st.sampled_from(ENTRY_KINDS)
verdicts = st.sampled_from(VERDICTS)

entries = st.builds(
    Entry,
    seq=st.just(1),
    round=st.integers(min_value=0, max_value=1000),
    kind=entry_kinds,
    text=filled_text,
    source=filled_text,
    at=days,
    head=optional(short_heads),
    verdict=optional(verdicts),
    cite=optional(filled_text),
    quote=optional(filled_text),
    addr=optional(filled_text),
    rests_on=optional(filled_text),
    refute=optional(filled_text),
    diagram=optional(filled_text),
    supersedes=st.builds(tuple, st.lists(free_text, max_size=3)),
)

pooled_entries = st.builds(
    Entry,
    seq=st.integers(min_value=1, max_value=3),
    round=st.integers(min_value=0, max_value=5),
    kind=entry_kinds,
    text=words,
    source=st.just('scout'),
    at=st.just(MOMENT),
    supersedes=st.builds(tuple, st.lists(st.sampled_from(POOLED_REFS), max_size=3)),
    thread=st.sampled_from(POOLED_THREADS),
)

capabilities = st.builds(
    Capabilities,
    languages=st.builds(tuple, st.lists(free_text, max_size=4)),
)

cases = st.builds(
    Case,
    id=free_text,
    target=free_text,
    kind=st.sampled_from(CASE_KINDS),
    bar=free_text,
    created=moments,
    publish=st.booleans(),
    head=optional(full_heads),
    page_url=optional(free_text),
    capabilities=capabilities,
)
