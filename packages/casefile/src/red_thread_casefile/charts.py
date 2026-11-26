"""The case map: each thread as a line of its entries, and what retired what, in mermaid."""

from dataclasses import dataclass
from itertools import chain, pairwise
from typing import TYPE_CHECKING

from red_thread_core.charts import clean_label

from red_thread_casefile.domain import order_thread

if TYPE_CHECKING:
    from collections.abc import Mapping

    from red_thread_casefile.domain import Entry, Ledger

MAIN_LEDGER = 'main ledger'


def label_node(entry: Entry) -> str:
    return f'{entry.ref} {entry.kind}: {clean_label(entry.text)}'


@dataclass(slots=True, kw_only=True, frozen=True)
class CaseMap:
    entries: tuple[Entry, ...]
    retired: frozenset[str]
    names: Mapping[str, str]

    @property
    def threads(self) -> tuple[str | None, ...]:
        found = {entry.thread for entry in self.entries}
        named = sorted((name for name in found if name is not None), key=order_thread)
        main = (None,) if None in found else ()
        return (*main, *named)

    def write_node(self, entry: Entry) -> str:
        style = 'retired' if entry.ref in self.retired else entry.kind
        return f'    {self.names[entry.ref]}["{label_node(entry)}"]:::k_{style}'

    def write_thread(self, thread: str | None) -> list[str]:
        entries = [entry for entry in self.entries if entry.thread == thread]
        names = [self.names[entry.ref] for entry in entries]
        links = (f'    {before} --- {after}' for before, after in pairwise(names))
        group = thread or 'main'
        title = thread or MAIN_LEDGER
        return [f'  subgraph {group}["{title}"]', *map(self.write_node, entries), *links, '  end']

    def write_retirements(self, entry: Entry) -> list[str]:
        known = (ref for ref in entry.supersedes if ref in self.names)
        return [f'  {self.names[entry.ref]} -. retires .-> {self.names[ref]}' for ref in known]

    def render(self) -> tuple[str, ...]:
        threads = chain.from_iterable(map(self.write_thread, self.threads))
        retirements = chain.from_iterable(map(self.write_retirements, self.entries))
        return (*threads, *retirements)


def create_case_map(ledger: Ledger) -> CaseMap:
    names = {entry.ref: f'n{index}' for index, entry in enumerate(ledger.entries)}
    return CaseMap(entries=ledger.entries, retired=ledger.retired, names=names)
