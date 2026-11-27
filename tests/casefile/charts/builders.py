"""Ledgers for the case map: findings spread over threads, some retiring earlier ones."""

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_casefile.domain import CaseLedger

from tests.casefile.ledger.builders import create_finding

if TYPE_CHECKING:
    from collections.abc import Sequence

    from red_thread_casefile.domain import CaseFinding, FindingKind

DANGLING_REF = 'T99.e1'


@dataclass(slots=True, kw_only=True, frozen=True)
class FindingSpec:
    thread: str | None
    kind: FindingKind
    text: str
    retires: tuple[int, ...] = ()
    dangling: bool = False


def pick_retired(earlier: list[CaseFinding], picks: tuple[int, ...]) -> tuple[str, ...]:
    if not earlier:
        return ()
    finding_ids = (earlier[pick % len(earlier)].finding_id for pick in picks)
    return tuple(dict.fromkeys(finding_ids))


def create_threaded_ledger(specs: Sequence[FindingSpec]) -> CaseLedger:
    counted: Counter[str | None] = Counter()
    findings: list[CaseFinding] = []
    for spec in specs:
        counted[spec.thread] += 1
        retired = pick_retired(findings, spec.retires)
        dangling = (DANGLING_REF,) * spec.dangling
        findings.append(
            create_finding(
                finding_number=counted[spec.thread],
                thread=spec.thread,
                kind=spec.kind,
                text=spec.text,
                supersedes=(*retired, *dangling),
            )
        )
    return CaseLedger(findings=tuple(findings))
