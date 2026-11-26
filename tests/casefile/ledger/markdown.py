"""A case and its entries written as Markdown, the way a skill or a lead writes them by hand."""

from collections import defaultdict
from dataclasses import dataclass, field
from itertools import groupby
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import msgspec
from msgspec.structs import replace
from red_thread_casefile.domain import (
    BLOCK_CLOSE,
    BLOCK_OPEN,
    CASE_FILE,
    ENTRY_MARK,
    THREAD_HOME,
    THREAD_SUFFIX,
    EntryRecord,
    RoundStamp,
)
from red_thread_casefile.schemas import write_case_file

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from red_thread_casefile.domain import Case, Entry


def name_file(thread: str | None) -> str:
    return CASE_FILE if thread is None else f'{THREAD_HOME}/{thread}{THREAD_SUFFIX}'


def append_text(case: Path, text: str, thread: str | None = None) -> None:
    path = case.joinpath(name_file(thread))
    earlier = path.read_text(encoding='utf-8') if path.is_file() else ''
    joiner = '\n' if earlier else ''
    path.write_text(f'{earlier}{joiner}{text}', encoding='utf-8')


def stamp_entry(entry: Entry) -> RoundStamp:
    return RoundStamp(number=entry.round, day=entry.at, head=entry.head)


def write_block(entry: Entry) -> str:
    fields = {name: getattr(entry, name) for name in EntryRecord.__struct_fields__}
    record = msgspec.convert(fields, EntryRecord)
    return msgspec.yaml.encode(record).decode()


def write_entry(entry: Entry) -> str:
    return f'{ENTRY_MARK}e{entry.seq}\n\n{BLOCK_OPEN}\n{write_block(entry)}{BLOCK_CLOSE}\n'


def write_round(stamp: RoundStamp, entries: Iterable[Entry]) -> str:
    blocks = '\n'.join(map(write_entry, entries))
    return f'{stamp.heading}\n\n{blocks}'


def write_rounds(entries: Iterable[Entry]) -> str:
    rounds = (write_round(stamp, group) for stamp, group in groupby(entries, key=stamp_entry))
    return '\n'.join(rounds)


def write_case_text(case: Case, entries: Iterable[Entry] = ()) -> str:
    rounds = write_rounds(entries)
    opening = write_case_file(case)
    return f'{opening}\n{rounds}' if rounds else opening


def write_thread_text(entries: Iterable[Entry]) -> str:
    return write_rounds(entries)


@runtime_checkable
class TextSink(Protocol):
    def write(self, name: str, text: str) -> None: ...


def start_files() -> defaultdict[str | None, list[Entry]]:
    return defaultdict(list)


@dataclass(slots=True, kw_only=True, frozen=True)
class CaseScribe:
    sink: TextSink
    cases: list[Case]
    files: defaultdict[str | None, list[Entry]] = field(default_factory=start_files)

    @property
    def case(self) -> Case:
        return self.cases[-1]

    def frame(self, case: Case) -> None:
        self.cases[:] = [case]
        self.sink.write(CASE_FILE, write_case_text(case, self.files[None]))

    def seed(self, thread: str | None, *entries: Entry) -> None:
        self.files[thread].extend(replace(entry, thread=thread) for entry in entries)
        held = self.files[thread]
        text = write_case_text(self.case, held) if thread is None else write_thread_text(held)
        self.sink.write(name_file(thread), text)
