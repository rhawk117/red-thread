"""The case map: each thread as a line of its findings, and what retired what, in mermaid."""

from dataclasses import dataclass
from itertools import chain, pairwise
from typing import TYPE_CHECKING

from red_thread_core.charts import clean_label

from red_thread_casefile.domain import order_thread

if TYPE_CHECKING:
    from collections.abc import Mapping

    from red_thread_casefile.domain import CaseFinding, CaseLedger

MAIN_LEDGER = 'main ledger'


def label_node(finding: CaseFinding) -> str:
    return f'{finding.finding_id} {finding.kind}: {clean_label(finding.text)}'


@dataclass(slots=True, kw_only=True, frozen=True)
class CaseMap:
    findings: tuple[CaseFinding, ...]
    retired: frozenset[str]
    names: Mapping[str, str]

    @property
    def threads(self) -> tuple[str | None, ...]:
        found = {finding.thread for finding in self.findings}
        named = sorted((name for name in found if name is not None), key=order_thread)
        main = (None,) if None in found else ()
        return (*main, *named)

    def write_node(self, finding: CaseFinding) -> str:
        style = 'retired' if finding.finding_id in self.retired else finding.kind
        return f'    {self.names[finding.finding_id]}["{label_node(finding)}"]:::k_{style}'

    def write_thread(self, thread: str | None) -> list[str]:
        findings = [finding for finding in self.findings if finding.thread == thread]
        names = [self.names[finding.finding_id] for finding in findings]
        links = (f'    {before} --- {after}' for before, after in pairwise(names))
        group = thread or 'main'
        title = thread or MAIN_LEDGER
        return [f'  subgraph {group}["{title}"]', *map(self.write_node, findings), *links, '  end']

    def write_retirements(self, finding: CaseFinding) -> list[str]:
        known = (finding_id for finding_id in finding.supersedes if finding_id in self.names)
        return [
            f'  {self.names[finding.finding_id]} -. retires .-> {self.names[finding_id]}'
            for finding_id in known
        ]

    def render(self) -> tuple[str, ...]:
        threads = chain.from_iterable(map(self.write_thread, self.threads))
        retirements = chain.from_iterable(map(self.write_retirements, self.findings))
        return (*threads, *retirements)


def create_case_map(ledger: CaseLedger) -> CaseMap:
    names = {finding.finding_id: f'n{index}' for index, finding in enumerate(ledger.findings)}
    return CaseMap(findings=ledger.findings, retired=ledger.retired, names=names)
