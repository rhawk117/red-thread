"""Values, factories and harnesses the casefile tests share."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_casefile.domain import Case, CaseFinding
from red_thread_casefile.packaged import load_wording
from red_thread_casefile.services import CaseFile

from tests.casefile.ledger.markdown import CaseScribe, write_case_text
from tests.casefile.ledger.memory import HEAD, SHORT_HEAD, MemoryCaseRepository, MemorySourceTree
from tests.codec import YAML
from tests.core.timekeeping.clock import DAY, MOMENT, FixedClock

if TYPE_CHECKING:
    from datetime import date

    from red_thread_casefile.domain import FindingKind, Verdict
    from red_thread_casefile.errors import CaseFileError
    from red_thread_casefile.services import Checked

CASE_ID = '20261121-retry-queue-slowdown'
URL_CITE = 'https://example.invalid/docs/retries#backoff'
QUEUE_PATH = 'src/queue.py'
PAGE_URL = 'https://claude.ai/artifact/retry-queue'
KNOWN = {
    'kind': 'known',
    'text': 'the sleep blocks the queue',
    'source': 'scout',
    'cite': 'src/queue.py:3',
    'quote': 'time.sleep(job.delay)',
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


def create_finding(
    *,
    finding_number: int = 1,
    thread: str | None = None,
    kind: FindingKind = 'open',
    text: str = 'the retry queue stalls',
    source: str = 'scout',
    round_number: int = 1,
    at: date = DAY,
    head: str | None = SHORT_HEAD,
    verdict: Verdict | None = None,
    citation: str | None = None,
    quote: str | None = None,
    code_address: str | None = None,
    rests_on: str | None = None,
    refuted_if: str | None = None,
    diagram: str | None = None,
    supersedes: tuple[str, ...] = (),
) -> CaseFinding:
    return CaseFinding(
        finding_number=finding_number,
        round=round_number,
        kind=kind,
        text=text,
        source=source,
        at=at,
        head=head,
        verdict=verdict,
        citation=citation,
        quote=quote,
        code_address=code_address,
        rests_on=rests_on,
        refuted_if=refuted_if,
        diagram=diagram,
        supersedes=supersedes,
        thread=thread,
    )


def create_valid_finding(kind: FindingKind, finding_number: int = 1) -> CaseFinding:
    finding = create_finding(
        finding_number=finding_number, kind=kind, text=f'a {kind} about the queue'
    )
    if kind == 'known':
        return finding.replace_with(citation=URL_CITE, verdict='VERIFIED')

    if kind == 'hypothesis':
        return finding.replace_with(refuted_if='the stall disappears when the sleep is removed')

    if kind == 'ruled_out':
        return finding.replace_with(citation=URL_CITE)

    if kind == 'decision':
        return finding.replace_with(source='user')

    return finding


@dataclass(slots=True, kw_only=True, frozen=True)
class CaseHarness:
    repository: MemoryCaseRepository
    tree: MemorySourceTree
    clock: FixedClock
    casefile: CaseFile
    scribe: CaseScribe

    @property
    def findings(self) -> tuple[CaseFinding, ...]:
        return self.casefile.load().ledger.findings

    def seed(self, thread: str | None, *findings: CaseFinding) -> None:
        self.scribe.seed(thread, *findings)

    def frame(self, case: Case) -> None:
        self.scribe.frame(case)

    def check(self) -> Checked:
        return self.casefile.check()

    def find_problems(self) -> tuple[CaseFileError, ...]:
        return self.check().problems


def create_case_harness() -> CaseHarness:
    repository = MemoryCaseRepository()
    tree = MemorySourceTree(files={QUEUE_PATH: QUEUE_LINES})
    clock = FixedClock()
    casefile = CaseFile(
        repository=repository, tree=tree, clock=clock, wording=load_wording(), codec=YAML
    )
    scribe = CaseScribe(sink=repository, cases=[create_case()])
    return CaseHarness(
        repository=repository, tree=tree, clock=clock, casefile=casefile, scribe=scribe
    )


def create_framed_harness() -> CaseHarness:
    harness = create_case_harness()
    harness.repository.create(write_case_text(create_case()))
    return harness
