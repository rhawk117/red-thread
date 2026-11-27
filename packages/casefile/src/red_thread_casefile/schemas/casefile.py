"""The case file both ways: its Markdown files read into findings, and the scaffold init writes."""

from dataclasses import dataclass
from itertools import chain, pairwise
from operator import attrgetter
from typing import TYPE_CHECKING

import msgspec
from red_thread_core.dto import DTO
from red_thread_core.errors import MalformedDocumentError
from red_thread_core.frontmatter import FENCE, FenceReasons, FrontSplit, split_frontmatter
from red_thread_core.lines import Line, cut_at, number_lines, split_lines, trim
from red_thread_core.timekeeping import read_day, write_moment

from red_thread_casefile.domain import (
    BLOCK_CLOSE,
    BLOCK_OPEN,
    CASE_FILE,
    FINDING_HEADING,
    FINDING_MARK,
    NO_HEAD,
    ROUND_HEADING,
    ROUND_MARK,
    THREAD_NAME,
    TITLE_MARK,
    Case,
    CaseFinding,
    CaseLedger,
    CaseRecord,
    FindingBlock,
    FindingLocation,
    LocatedFinding,
    RoundStamp,
)
from red_thread_casefile.errors import (
    CaseFileError,
    FindingBeforeRoundError,
    MalformedBlockError,
    MalformedCaseError,
    MalformedFindingHeadingError,
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

    from red_thread_core.codec import Codec
    from red_thread_core.lines import Cut

    from red_thread_casefile.domain import LedgerSource

type Problems = tuple[CaseFileError, ...]
type Reading = LocatedFinding | CaseFileError
type Block = tuple[FindingBlock | CaseFileError, *tuple[CaseFileError, ...]]


class FileReading(DTO, frozen=True, kw_only=True, gc=False):
    located: tuple[LocatedFinding, ...] = ()
    problems: Problems = ()


class Front(DTO, frozen=True, kw_only=True, gc=False):
    body: tuple[Line, ...]
    case: Case | None = None
    problems: Problems = ()


class CaseReading(DTO, frozen=True, kw_only=True, gc=False):
    case: Case | None
    located: tuple[LocatedFinding, ...]
    problems: Problems

    @property
    def ledger(self) -> CaseLedger:
        return CaseLedger(findings=tuple(map(attrgetter('finding'), self.located)))


FENCE_REASONS = FenceReasons(
    no_opening='it does not open with a --- line', no_closing='it has no closing --- line'
)


def split_readings(readings: Iterable[Reading]) -> FileReading:
    held = tuple(readings)
    return FileReading(
        located=tuple(item for item in held if isinstance(item, LocatedFinding)),
        problems=tuple(item for item in held if not isinstance(item, LocatedFinding)),
    )


def name_finding_id(thread: str | None, finding_number: int) -> str:
    if thread is None:
        return f'e{finding_number}'
    return f'{thread}.e{finding_number}'


def list_numbers(body: tuple[Line, ...]) -> tuple[Numbered, ...]:
    heads = (part.head for part in cut_at(body, FINDING_MARK).parts)
    found = ((head, FINDING_HEADING.fullmatch(head.mark)) for head in heads)
    return tuple(
        Numbered(line=head, finding_number=int(match['finding_number']))
        for head, match in found
        if match
    )


def list_rounds(body: tuple[Line, ...]) -> tuple[Numbered, ...]:
    heads = (part.head for part in cut_at(body, ROUND_MARK).parts)
    found = ((head, ROUND_HEADING.fullmatch(head.mark)) for head in heads)
    return tuple(
        Numbered(line=head, finding_number=int(match['round'])) for head, match in found if match
    )


def decode_record(
    codec: Codec, text: str, location: FindingLocation
) -> FindingBlock | MalformedBlockError:
    decoded = codec.decode(text, FindingBlock)
    if isinstance(decoded, MalformedDocumentError):
        return MalformedBlockError(location=location, reason=decoded.reason)

    return decoded


@dataclass(slots=True, kw_only=True, frozen=True)
class LedgerReader:
    source: LedgerSource
    codec: Codec

    def locate(self, line: Line, finding_number: int | None = None) -> FindingLocation:
        finding_id = (
            None if finding_number is None else name_finding_id(self.source.thread, finding_number)
        )
        return FindingLocation(file=self.source.name, line=line.number, finding_id=finding_id)

    def judge_loose(self, line: Line) -> CaseFileError | None:
        if line.is_blank:
            return None
        return StrayTextError(location=self.locate(line))

    def judge_opening(self, line: Line) -> CaseFileError | None:
        if line.text.startswith(TITLE_MARK):
            return None
        return self.judge_loose(line)

    def read_stamp(self, line: Line) -> RoundStamp | MalformedRoundError:
        matched = ROUND_HEADING.fullmatch(line.mark)
        day = None if matched is None else read_day(matched['day'])
        if matched is None or day is None:
            return MalformedRoundError(location=self.locate(line))
        head = None if matched['head'] == NO_HEAD else matched['head']
        return RoundStamp(number=int(matched['round']), day=day, head=head)

    def read_block(self, lines: tuple[Line, ...], location: FindingLocation) -> Block:
        if not lines or lines[0].text.rstrip() != BLOCK_OPEN:
            return (MissingBlockError(location=location),)

        closers = (
            index for index, line in enumerate(lines) if index and line.text.rstrip() == BLOCK_CLOSE
        )
        closing = next(closers, None)
        if closing is None:
            return (MissingBlockError(location=location),)

        stray = filter(None, map(self.judge_loose, lines[closing + 1 :]))
        record = decode_record(
            self.codec, '\n'.join(line.text for line in lines[1:closing]), location
        )
        return (record, *stray)

    def read_finding(self, cut: Cut, stamp: RoundStamp) -> tuple[Reading, ...]:
        matched = FINDING_HEADING.fullmatch(cut.head.mark)
        if matched is None:
            return (MalformedFindingHeadingError(location=self.locate(cut.head)),)

        finding_number = int(matched['finding_number'])
        location = self.locate(cut.head, finding_number)
        record, *rest = self.read_block(trim(cut.body), location)
        if not isinstance(record, FindingBlock):
            return (record, *rest)

        finding = CaseFinding(
            **record.as_dict(),
            finding_number=finding_number,
            round=stamp.number,
            at=stamp.day,
            head=stamp.head,
            thread=self.source.thread,
        )
        return (LocatedFinding(finding=finding, location=location), *rest)

    def read_round(self, cut: Cut) -> tuple[Reading, ...]:
        stamp = self.read_stamp(cut.head)
        if isinstance(stamp, MalformedRoundError):
            return (stamp,)

        findings = cut_at(cut.body, FINDING_MARK)
        loose = filter(None, map(self.judge_loose, findings.preamble))
        read = chain.from_iterable(self.read_finding(part, stamp) for part in findings.parts)
        return (*loose, *read)

    def find_sequence_problems(
        self, body: tuple[Line, ...]
    ) -> tuple[NumberingError | RoundOrderError, ...]:
        start = Numbered(line=Line(number=0, text=''), finding_number=0)
        findings = pairwise((start, *list_numbers(body)))
        numbering = (
            NumberingError(
                location=self.locate(later.line, later.finding_number),
                expected=earlier.finding_number + 1,
            )
            for earlier, later in findings
            if later.finding_number != earlier.finding_number + 1
        )
        order = (
            RoundOrderError(
                location=self.locate(later.line),
                number=later.finding_number,
                previous=earlier.finding_number,
            )
            for earlier, later in pairwise(list_rounds(body))
            if later.finding_number <= earlier.finding_number
        )
        return (*numbering, *order)

    def read_opening(self, opening: tuple[Line, ...]) -> tuple[CaseFileError, ...]:
        findings = cut_at(opening, FINDING_MARK)
        loose = filter(None, map(self.judge_opening, findings.preamble))
        early = (
            FindingBeforeRoundError(location=self.locate(part.head)) for part in findings.parts
        )
        return (*loose, *early)

    def read(self, body: tuple[Line, ...]) -> FileReading:
        rounds = cut_at(body, ROUND_MARK)
        opening = self.read_opening(rounds.preamble)
        read = chain.from_iterable(map(self.read_round, rounds.parts))
        found = split_readings((*opening, *read))
        sequence = self.find_sequence_problems(body)
        return FileReading(located=found.located, problems=(*found.problems, *sequence))


def load_record(reading: CaseReading) -> CaseRecord | MalformedCaseError:
    if reading.case is None or reading.problems:
        return MalformedCaseError(problems=reading.problems)
    return CaseRecord(case=reading.case, ledger=reading.ledger)


def write_title(target: str) -> str:
    return f'{TITLE_MARK}{" ".join(target.split())}'


@dataclass(slots=True, kw_only=True, frozen=True)
class CaseFileSchema:
    codec: Codec

    def decode_case(self, text: str) -> Case | MalformedFrontmatterError:
        decoded = self.codec.decode(text, dict[str, object])
        if isinstance(decoded, MalformedDocumentError):
            return MalformedFrontmatterError(file=CASE_FILE, reason=decoded.reason)

        try:
            case = Case.convert(decoded, strict=False)
        except msgspec.ValidationError as error:
            return MalformedFrontmatterError(file=CASE_FILE, reason=str(error))
        return case

    def read_front(self, source: LedgerSource) -> Front:
        lines = split_lines(source.text)
        every = number_lines(lines, FIRST_LINE)
        if source.name != CASE_FILE:
            return Front(body=every)

        split = split_frontmatter(lines)
        if not isinstance(split, FrontSplit):
            reason = FENCE_REASONS.explain(split)
            problem = MalformedFrontmatterError(file=CASE_FILE, reason=reason)
            kept = () if split == 'no_closing' else every
            return Front(body=kept, problems=(problem,))

        decoded = self.decode_case('\n'.join(split.front))
        body = every[split.closing + 1 :]
        if isinstance(decoded, MalformedFrontmatterError):
            return Front(body=body, problems=(decoded,))

        return Front(body=body, case=decoded)

    def read_source(self, source: LedgerSource) -> FileReading:
        if source.thread is not None and not THREAD_NAME.fullmatch(source.thread):
            return FileReading(problems=(StrayThreadFileError(file=source.name),))

        front = self.read_front(source)
        read = LedgerReader(source=source, codec=self.codec).read(front.body)
        return FileReading(located=read.located, problems=(*front.problems, *read.problems))

    def read(self, sources: Sequence[LedgerSource]) -> CaseReading:
        case = next((source for source in sources if source.name == CASE_FILE), None)
        front = None if case is None else self.read_front(case)
        readings = tuple(map(self.read_source, sources))
        return CaseReading(
            case=None if front is None else front.case,
            located=tuple(chain.from_iterable(map(attrgetter('located'), readings))),
            problems=tuple(chain.from_iterable(map(attrgetter('problems'), readings))),
        )

    def write(self, case: Case) -> str:
        written = {**msgspec.to_builtins(case), 'created': write_moment(case.created)}
        fields = self.codec.encode_text(written)
        opening = RoundStamp(number=0, day=case.created.date(), head=case.head)
        return f'{FENCE}\n{fields}{FENCE}\n\n{write_title(case.target)}\n\n{opening.heading}\n'
