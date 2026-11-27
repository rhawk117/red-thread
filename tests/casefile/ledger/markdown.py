"""A case and its findings written as Markdown, the way a skill or a lead writes them by hand."""

from collections import defaultdict
from dataclasses import dataclass, field
from itertools import groupby
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from red_thread_casefile.domain import (
    BLOCK_CLOSE,
    BLOCK_OPEN,
    CASE_FILE,
    FINDING_MARK,
    THREAD_HOME,
    THREAD_SUFFIX,
    FindingBlock,
    RoundStamp,
)
from red_thread_casefile.schemas import CaseFileSchema

from tests.codec import YAML

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

    from red_thread_casefile.domain import Case, CaseFinding

SCHEMA = CaseFileSchema(codec=YAML)


def name_file(thread: str | None) -> str:
    return CASE_FILE if thread is None else f'{THREAD_HOME}/{thread}{THREAD_SUFFIX}'


def append_text(case: Path, text: str, thread: str | None = None) -> None:
    path = case.joinpath(name_file(thread))
    earlier = path.read_text(encoding='utf-8') if path.is_file() else ''
    joiner = '\n' if earlier else ''
    path.write_text(f'{earlier}{joiner}{text}', encoding='utf-8')


def stamp_finding(finding: CaseFinding) -> RoundStamp:
    return RoundStamp(number=finding.round, day=finding.at, head=finding.head)


def number_findings(written: Sequence[CaseFinding], thread: str | None) -> list[CaseFinding]:
    groups = groupby(written, key=stamp_finding)
    rounds = (
        finding.replace_with(round=number)
        for number, (_, group) in enumerate(groups, 1)
        for finding in group
    )
    return [
        finding.replace_with(finding_number=finding_number, thread=thread)
        for finding_number, finding in enumerate(rounds, 1)
    ]


def write_block(finding: CaseFinding) -> str:
    record = FindingBlock.convert(finding, from_attributes=True)
    return YAML.encode_text(record)


def write_finding(finding: CaseFinding) -> str:
    heading = f'{FINDING_MARK}e{finding.finding_number}'
    return f'{heading}\n\n{BLOCK_OPEN}\n{write_block(finding)}{BLOCK_CLOSE}\n'


def write_round(stamp: RoundStamp, findings: Iterable[CaseFinding]) -> str:
    blocks = '\n'.join(map(write_finding, findings))
    return f'{stamp.heading}\n\n{blocks}'


def write_rounds(findings: Iterable[CaseFinding]) -> str:
    rounds = (write_round(stamp, group) for stamp, group in groupby(findings, key=stamp_finding))
    return '\n'.join(rounds)


def write_case_text(case: Case, findings: Iterable[CaseFinding] = ()) -> str:
    rounds = write_rounds(findings)
    opening = SCHEMA.write(case)
    return f'{opening}\n{rounds}' if rounds else opening


def write_thread_text(findings: Iterable[CaseFinding]) -> str:
    return write_rounds(findings)


@runtime_checkable
class TextSink(Protocol):
    def write(self, name: str, text: str) -> None: ...


def start_files() -> defaultdict[str | None, list[CaseFinding]]:
    return defaultdict(list)


@dataclass(slots=True, kw_only=True, frozen=True)
class CaseScribe:
    sink: TextSink
    cases: list[Case]
    files: defaultdict[str | None, list[CaseFinding]] = field(default_factory=start_files)

    @property
    def case(self) -> Case:
        return self.cases[-1]

    def frame(self, case: Case) -> None:
        self.cases[:] = [case]
        self.sink.write(CASE_FILE, write_case_text(case, self.files[None]))

    def seed(self, thread: str | None, *findings: CaseFinding) -> None:
        self.files[thread].extend(finding.replace_with(thread=thread) for finding in findings)
        held = self.files[thread]
        text = write_case_text(self.case, held) if thread is None else write_thread_text(held)
        self.sink.write(name_file(thread), text)
