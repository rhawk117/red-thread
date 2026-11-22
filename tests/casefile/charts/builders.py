"""Ledgers for the case map: entries spread over threads, some retiring earlier ones."""

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_casefile.domain import Ledger

from tests.casefile.ledger.builders import create_entry

if TYPE_CHECKING:
    from collections.abc import Sequence

    from red_thread_casefile.domain import Entry, EntryKind

DANGLING_REF = 'T99.e1'


@dataclass(slots=True, kw_only=True, frozen=True)
class EntrySpec:
    thread: str | None
    kind: EntryKind
    text: str
    retires: tuple[int, ...] = ()
    dangling: bool = False


def pick_retired(earlier: list[Entry], picks: tuple[int, ...]) -> tuple[str, ...]:
    if not earlier:
        return ()
    refs = (earlier[pick % len(earlier)].ref for pick in picks)
    return tuple(dict.fromkeys(refs))


def create_threaded_ledger(specs: Sequence[EntrySpec]) -> Ledger:
    counted: Counter[str | None] = Counter()
    entries: list[Entry] = []
    for spec in specs:
        counted[spec.thread] += 1
        retired = pick_retired(entries, spec.retires)
        dangling = (DANGLING_REF,) * spec.dangling
        entries.append(
            create_entry(
                seq=counted[spec.thread],
                thread=spec.thread,
                kind=spec.kind,
                text=spec.text,
                supersedes=(*retired, *dangling),
            )
        )
    return Ledger(entries=tuple(entries))
