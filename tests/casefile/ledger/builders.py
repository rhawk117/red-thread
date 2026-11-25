"""Values, factories and harnesses the casefile tests share."""

import json
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.domain import Case, Draft, Entry
from red_thread_casefile.errors import BatchRejectedError
from red_thread_casefile.services import Batch, CaseFile

from tests.casefile.ledger.memory import (
    HEAD,
    MOMENT,
    FixedClock,
    MemoryCaseRepository,
    MemorySourceTree,
)

if TYPE_CHECKING:
    from red_thread_casefile.domain import EntryKind, Verdict
    from red_thread_casefile.errors import CaseFileError
    from red_thread_casefile.services import Added

CASE_ID = '20261121-retry-queue-slowdown'
URL_CITE = 'https://example.invalid/docs/retries#backoff'
QUEUE_PATH = 'src/queue.py'
PAGE_URL = 'https://claude.ai/artifact/retry-queue'
KNOWN = {
    'kind': 'known',
    'text': 'the sleep blocks the queue',
    'source': 'scout',
    'cite': 'src/queue.py:3',
}
QUEUE_LINES = (
    'import time',
    'def retry(job):',
    '    time.sleep(job.delay)',
    '    return job.run()',
)


def create_case() -> Case:
    return Case(
        id=CASE_ID,
        target='why the retry queue stalls',
        kind='root-cause',
        bar='name the line that stalls it',
        created=MOMENT,
        head=HEAD,
    )


def create_entry(
    *,
    seq: int = 1,
    thread: str | None = None,
    kind: EntryKind = 'open',
    text: str = 'the retry queue stalls',
    source: str = 'scout',
    round_number: int = 1,
    at: str = MOMENT,
    head: str | None = HEAD,
    verdict: Verdict | None = None,
    cite: str | None = None,
    quote: str | None = None,
    addr: str | None = None,
    rests_on: str | None = None,
    refute: str | None = None,
    diagram: str | None = None,
    supersedes: tuple[str, ...] = (),
) -> Entry:
    return Entry(
        seq=seq,
        round=round_number,
        kind=kind,
        text=text,
        source=source,
        at=at,
        head=head,
        verdict=verdict,
        cite=cite,
        quote=quote,
        addr=addr,
        rests_on=rests_on,
        refute=refute,
        diagram=diagram,
        supersedes=supersedes,
        thread=thread,
    )


def create_draft(position: int = 1, *, kind: EntryKind = 'open', source: str = 'scout') -> Draft:
    return Draft(position=position, kind=kind, text=f'a {kind} about the queue', source=source)


def create_valid_draft(kind: EntryKind, position: int = 1) -> Draft:
    draft = create_draft(position, kind=kind)
    if kind == 'known':
        return replace(draft, cite=URL_CITE, verdict='VERIFIED')

    if kind == 'hypothesis':
        return replace(draft, refute='the stall disappears when the sleep is removed')

    if kind == 'ruled_out':
        return replace(draft, cite=URL_CITE)

    if kind == 'decision':
        return replace(draft, source='user')

    return draft


def create_batch_text(*records: dict[str, object]) -> str:
    return json.dumps(list(records))


@dataclass(slots=True, kw_only=True, frozen=True)
class CaseHarness:
    repository: MemoryCaseRepository
    tree: MemorySourceTree
    clock: FixedClock
    casefile: CaseFile

    @property
    def entries(self) -> tuple[Entry, ...]:
        return self.repository.read_ledger().entries

    def seed(self, thread: str | None, *entries: Entry) -> None:
        self.repository.append(thread, entries)

    def add(self, *drafts: Draft, thread: str | None = None, round_number: int = 1) -> Added:
        return self.casefile.add(Batch(drafts=drafts, round=round_number, thread=thread))


def create_case_harness() -> CaseHarness:
    repository = MemoryCaseRepository()
    tree = MemorySourceTree(files={QUEUE_PATH: QUEUE_LINES})
    clock = FixedClock()
    casefile = CaseFile(repository=repository, tree=tree, clock=clock)
    return CaseHarness(repository=repository, tree=tree, clock=clock, casefile=casefile)


def create_framed_harness() -> CaseHarness:
    harness = create_case_harness()
    harness.repository.create(create_case())
    return harness


def reject_batch(
    harness: CaseHarness,
    *drafts: Draft,
    thread: str | None = None,
    problems: tuple[CaseFileError, ...] = (),
) -> BatchRejectedError:
    entries_before = harness.entries
    batch = Batch(drafts=drafts, round=1, thread=thread, problems=problems)
    with pytest.raises(BatchRejectedError) as raised:
        harness.casefile.add(batch)
    assert harness.entries == entries_before
    return raised.value
