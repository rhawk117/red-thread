"""The case file both ways: its Markdown files read into entries, and the scaffold init writes."""

from dataclasses import dataclass
from itertools import chain, pairwise
from operator import attrgetter
from typing import TYPE_CHECKING

import msgspec
from red_thread_core.frontmatter import FENCE, FenceReasons, decode_yaml, split_frontmatter
from red_thread_core.lines import Line, cut_at, number_lines, split_lines, trim

from red_thread_casefile.domain import (
    BLOCK_CLOSE,
    BLOCK_OPEN,
    CASE_FILE,
    ENTRY_HEADING,
    ENTRY_MARK,
    NO_HEAD,
    ROUND_HEADING,
    ROUND_MARK,
    THREAD_NAME,
    TITLE_MARK,
    Case,
    CaseRecord,
    Entry,
    EntryRecord,
    Ledger,
    Placed,
    RoundStamp,
    Spot,
    date_of,
    is_day,
)
from red_thread_casefile.errors import (
    CaseFileError,
    EntryBeforeRoundError,
    MalformedBlockError,
    MalformedCaseError,
    MalformedEntryHeadingError,
    MalformedFrontmatterError,
    MalformedRoundError,
    MissingBlockError,
    NumberingError,
    RoundOrderError,
    StrayTextError,
    StrayThreadFileError,
)
from red_thread_casefile.schemas.lines import FIRST_LINE, Numbered

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from red_thread_core.lines import Cut

    from red_thread_casefile.domain import LedgerSource

type Problems = tuple[CaseFileError, ...]
type Reading = Placed | CaseFileError
type Block = tuple[EntryRecord | CaseFileError, *tuple[CaseFileError, ...]]


@dataclass(slots=True, kw_only=True, frozen=True)
class FileReading:
    placed: tuple[Placed, ...] = ()
    problems: Problems = ()


@dataclass(slots=True, kw_only=True, frozen=True)
class Front:
    body: tuple[Line, ...]
    case: Case | None = None
    problems: Problems = ()


@dataclass(slots=True, kw_only=True, frozen=True)
class CaseReading:
    case: Case | None
    placed: tuple[Placed, ...]
    problems: Problems

    @property
    def ledger(self) -> Ledger:
        return Ledger(entries=tuple(map(attrgetter('entry'), self.placed)))


FENCE_REASONS = FenceReasons(
    no_opening='it does not open with a --- line', no_closing='it has no closing --- line'
)


def decode_case(name: str, text: str) -> Case | MalformedFrontmatterError:
    decoded = decode_yaml(text, Case)
    if isinstance(decoded, msgspec.DecodeError):
        return MalformedFrontmatterError(file=name, reason=str(decoded))

    return decoded


def decode_record(text: str, spot: Spot) -> EntryRecord | MalformedBlockError:
    decoded = decode_yaml(text, EntryRecord)
    if isinstance(decoded, msgspec.DecodeError):
        return MalformedBlockError(spot=spot, reason=str(decoded))

    return decoded


def read_front(source: LedgerSource) -> Front:
    lines = split_lines(source.text)
    every = number_lines(lines, FIRST_LINE)
    if source.name != CASE_FILE:
        return Front(body=every)

    split = split_frontmatter(lines)
    if isinstance(split, str):
        problem = MalformedFrontmatterError(file=CASE_FILE, reason=FENCE_REASONS.explain(split))
        kept = () if split == 'no_closing' else every
        return Front(body=kept, problems=(problem,))

    decoded = decode_case(CASE_FILE, '\n'.join(split.front))
    body = every[split.closing + 1 :]
    if isinstance(decoded, MalformedFrontmatterError):
        return Front(body=body, problems=(decoded,))

    return Front(body=body, case=decoded)


def split_readings(readings: Iterable[Reading]) -> FileReading:
    held = tuple(readings)
    return FileReading(
        placed=tuple(item for item in held if isinstance(item, Placed)),
        problems=tuple(item for item in held if not isinstance(item, Placed)),
    )


def name_ref(thread: str | None, seq: int) -> str:
    if thread is None:
        return f'e{seq}'
    return f'{thread}.e{seq}'


def list_numbers(body: tuple[Line, ...]) -> tuple[Numbered, ...]:
    heads = (part.head for part in cut_at(body, ENTRY_MARK).parts)
    found = ((head, ENTRY_HEADING.fullmatch(head.mark)) for head in heads)
    return tuple(Numbered(line=head, seq=int(match['seq'])) for head, match in found if match)


def list_rounds(body: tuple[Line, ...]) -> tuple[Numbered, ...]:
    heads = (part.head for part in cut_at(body, ROUND_MARK).parts)
    found = ((head, ROUND_HEADING.fullmatch(head.mark)) for head in heads)
    return tuple(Numbered(line=head, seq=int(match['round'])) for head, match in found if match)


@dataclass(slots=True, kw_only=True, frozen=True)
class LedgerReader:
    source: LedgerSource

    def locate(self, line: Line, seq: int | None = None) -> Spot:
        ref = None if seq is None else name_ref(self.source.thread, seq)
        return Spot(file=self.source.name, line=line.number, ref=ref)

    def judge_loose(self, line: Line) -> CaseFileError | None:
        if line.is_blank:
            return None
        return StrayTextError(spot=self.locate(line))

    def judge_opening(self, line: Line) -> CaseFileError | None:
        if line.text.startswith(TITLE_MARK):
            return None
        return self.judge_loose(line)

    def read_stamp(self, line: Line) -> RoundStamp | MalformedRoundError:
        matched = ROUND_HEADING.fullmatch(line.mark)
        if matched is None or not is_day(matched['day']):
            return MalformedRoundError(spot=self.locate(line))
        head = None if matched['head'] == NO_HEAD else matched['head']
        return RoundStamp(number=int(matched['round']), day=matched['day'], head=head)

    def read_block(self, lines: tuple[Line, ...], spot: Spot) -> Block:
        if not lines or lines[0].text.rstrip() != BLOCK_OPEN:
            return (MissingBlockError(spot=spot),)

        closers = (
            index for index, line in enumerate(lines) if index and line.text.rstrip() == BLOCK_CLOSE
        )
        closing = next(closers, None)
        if closing is None:
            return (MissingBlockError(spot=spot),)

        stray = filter(None, map(self.judge_loose, lines[closing + 1 :]))
        record = decode_record('\n'.join(line.text for line in lines[1:closing]), spot)
        return (record, *stray)

    def read_entry(self, cut: Cut, stamp: RoundStamp) -> tuple[Reading, ...]:
        matched = ENTRY_HEADING.fullmatch(cut.head.mark)
        if matched is None:
            return (MalformedEntryHeadingError(spot=self.locate(cut.head)),)

        seq = int(matched['seq'])
        spot = self.locate(cut.head, seq)
        record, *rest = self.read_block(trim(cut.body), spot)
        if not isinstance(record, EntryRecord):
            return (record, *rest)

        entry = Entry(
            **record.as_dict(),
            seq=seq,
            round=stamp.number,
            at=stamp.day,
            head=stamp.head,
            thread=self.source.thread,
        )
        return (Placed(entry=entry, spot=spot), *rest)

    def read_round(self, cut: Cut) -> tuple[Reading, ...]:
        stamp = self.read_stamp(cut.head)
        if isinstance(stamp, MalformedRoundError):
            return (stamp,)

        entries = cut_at(cut.body, ENTRY_MARK)
        loose = filter(None, map(self.judge_loose, entries.preamble))
        read = chain.from_iterable(self.read_entry(part, stamp) for part in entries.parts)
        return (*loose, *read)

    def find_sequence_problems(
        self, body: tuple[Line, ...]
    ) -> tuple[NumberingError | RoundOrderError, ...]:
        start = Numbered(line=Line(number=0, text=''), seq=0)
        entries = pairwise((start, *list_numbers(body)))
        numbering = (
            NumberingError(spot=self.locate(later.line, later.seq), expected=earlier.seq + 1)
            for earlier, later in entries
            if later.seq != earlier.seq + 1
        )
        order = (
            RoundOrderError(spot=self.locate(later.line), number=later.seq, previous=earlier.seq)
            for earlier, later in pairwise(list_rounds(body))
            if later.seq <= earlier.seq
        )
        return (*numbering, *order)

    def read_opening(self, opening: tuple[Line, ...]) -> tuple[CaseFileError, ...]:
        entries = cut_at(opening, ENTRY_MARK)
        loose = filter(None, map(self.judge_opening, entries.preamble))
        early = (EntryBeforeRoundError(spot=self.locate(part.head)) for part in entries.parts)
        return (*loose, *early)

    def read(self, body: tuple[Line, ...]) -> FileReading:
        rounds = cut_at(body, ROUND_MARK)
        opening = self.read_opening(rounds.preamble)
        read = chain.from_iterable(map(self.read_round, rounds.parts))
        found = split_readings((*opening, *read))
        sequence = self.find_sequence_problems(body)
        return FileReading(placed=found.placed, problems=(*found.problems, *sequence))


def read_source(source: LedgerSource) -> FileReading:
    if source.thread is not None and not THREAD_NAME.fullmatch(source.thread):
        return FileReading(problems=(StrayThreadFileError(file=source.name),))

    front = read_front(source)
    read = LedgerReader(source=source).read(front.body)
    return FileReading(placed=read.placed, problems=(*front.problems, *read.problems))


def read_case_file(sources: Sequence[LedgerSource]) -> CaseReading:
    case = next((source for source in sources if source.name == CASE_FILE), None)
    front = None if case is None else read_front(case)
    readings = tuple(map(read_source, sources))
    return CaseReading(
        case=None if front is None else front.case,
        placed=tuple(chain.from_iterable(map(attrgetter('placed'), readings))),
        problems=tuple(chain.from_iterable(map(attrgetter('problems'), readings))),
    )


def load_record(reading: CaseReading) -> CaseRecord | MalformedCaseError:
    if reading.case is None or reading.problems:
        return MalformedCaseError(problems=reading.problems)
    return CaseRecord(case=reading.case, ledger=reading.ledger)


def write_title(target: str) -> str:
    return f'{TITLE_MARK}{" ".join(target.split())}'


def write_case_file(case: Case) -> str:
    fields = msgspec.yaml.encode(case).decode()
    opening = RoundStamp(number=0, day=date_of(case.created), head=case.head)
    return f'{FENCE}\n{fields}{FENCE}\n\n{write_title(case.target)}\n\n{opening.heading}\n'
