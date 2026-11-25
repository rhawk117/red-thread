"""Translation between ledger lines, submitted batches and the domain values."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import msgspec

from red_thread_casefile.domain import ENTRY_KINDS, VERDICTS, Case, Draft, Entry
from red_thread_casefile.errors import (
    InvalidFieldError,
    MalformedBatchError,
    MalformedPlanError,
    UnknownFieldError,
)
from red_thread_casefile.lenses import Plan

if TYPE_CHECKING:
    from collections.abc import Mapping

    from red_thread_casefile.domain import EntryKind, Verdict

type ShapeProblem = UnknownFieldError | InvalidFieldError

OPTIONAL_TEXT_FIELDS = ('cite', 'quote', 'addr', 'rests_on', 'refute', 'diagram')
DRAFT_FIELDS = ('kind', 'text', 'source', 'verdict', *OPTIONAL_TEXT_FIELDS, 'supersedes')


def find_kind(value: object) -> EntryKind | None:
    return next((kind for kind in ENTRY_KINDS if kind == value), None)


def find_verdict(value: object) -> Verdict | None:
    return next((verdict for verdict in VERDICTS if verdict == value), None)


def read_text(record: Mapping[str, object], name: str) -> str | None:
    value = record.get(name)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


@dataclass(slots=True, kw_only=True, frozen=True)
class DraftRecord:
    position: int
    record: Mapping[str, object]

    @property
    def unknown_field(self) -> str | None:
        return next((name for name in self.record if name not in DRAFT_FIELDS), None)

    @property
    def malformed_text_field(self) -> str | None:
        present = (name for name in OPTIONAL_TEXT_FIELDS if self.record.get(name) is not None)
        return next((name for name in present if not isinstance(self.record[name], str)), None)

    @property
    def supersedes(self) -> tuple[str, ...] | None:
        value = self.record.get('supersedes') or []
        if not isinstance(value, list):
            return None
        refs = tuple(ref for ref in value if isinstance(ref, str))
        if len(refs) != len(value):
            return None
        return refs

    def reject(self, field: str, expected: str) -> InvalidFieldError:
        return InvalidFieldError(position=self.position, field=field, expected=expected)

    def get_field_problem(self) -> ShapeProblem | None:
        if (unknown := self.unknown_field) is not None:
            return UnknownFieldError(position=self.position, field=unknown, allowed=DRAFT_FIELDS)

        verdict = self.record.get('verdict')
        if verdict is not None and not find_verdict(verdict):
            return self.reject('verdict', 'left out, or one of ' + ', '.join(VERDICTS))

        if (malformed := self.malformed_text_field) is not None:
            return self.reject(malformed, 'a string')

        return None

    def parse(self) -> Draft | ShapeProblem:
        kind = find_kind(self.record.get('kind'))
        if not kind:
            return self.reject('kind', 'one of ' + ', '.join(ENTRY_KINDS))

        text = read_text(self.record, 'text')
        if text is None:
            return self.reject('text', 'a non-empty string')

        source = read_text(self.record, 'source')
        if source is None:
            return self.reject('source', 'the agent that found it, user or primary')

        supersedes = self.supersedes
        if supersedes is None:
            return self.reject('supersedes', 'a list of entry refs such as ["e3", "T1.e2"]')

        return self.get_field_problem() or Draft(
            position=self.position,
            kind=kind,
            text=text,
            source=source,
            supersedes=supersedes,
            verdict=find_verdict(self.record.get('verdict')),
            cite=read_text(self.record, 'cite'),
            quote=read_text(self.record, 'quote'),
            addr=read_text(self.record, 'addr'),
            rests_on=read_text(self.record, 'rests_on'),
            refute=read_text(self.record, 'refute'),
            diagram=read_text(self.record, 'diagram'),
        )


@dataclass(slots=True, kw_only=True, frozen=True)
class ParsedBatch:
    drafts: tuple[Draft, ...]
    problems: tuple[ShapeProblem, ...]


def load_records(text: str) -> list[Any]:
    try:
        loaded = msgspec.json.decode(text)
    except msgspec.DecodeError as error:
        raise MalformedBatchError(reason=f'it is not JSON ({error})') from error
    records = [loaded] if isinstance(loaded, dict) else loaded
    if not isinstance(records, list) or not records:
        raise MalformedBatchError(reason='it holds no entries')
    if not all(isinstance(record, dict) for record in records):
        raise MalformedBatchError(reason='an item is not a JSON object')
    return records


def parse_batch(text: str) -> ParsedBatch:
    numbered = enumerate(load_records(text), 1)
    parsed = tuple(
        DraftRecord(position=position, record=record).parse() for position, record in numbered
    )
    return ParsedBatch(
        drafts=tuple(item for item in parsed if isinstance(item, Draft)),
        problems=tuple(item for item in parsed if not isinstance(item, Draft)),
    )


def entry_to_line(entry: Entry) -> str:
    return msgspec.json.encode(msgspec.structs.replace(entry, thread=None)).decode()


def entry_from_line(line: str, thread: str | None) -> Entry:
    return msgspec.structs.replace(msgspec.json.decode(line, type=Entry), thread=thread)


def case_to_text(case: Case) -> str:
    return msgspec.json.format(msgspec.json.encode(case), indent=2).decode() + '\n'


def case_from_text(text: str) -> Case:
    return msgspec.json.decode(text, type=Case)


PLAN_TEXT_FIELDS = ('title', 'goal')
PLAN_REF_FIELDS = ('include', 'blocking')


def is_ref_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(ref, str) for ref in value)


@dataclass(slots=True, kw_only=True, frozen=True)
class PlanRecord:
    record: Mapping[str, object]

    @property
    def unknown_field(self) -> str | None:
        allowed = (*PLAN_TEXT_FIELDS, *PLAN_REF_FIELDS)
        return next((name for name in self.record if name not in allowed), None)

    @property
    def malformed_text_field(self) -> str | None:
        present = (name for name in PLAN_TEXT_FIELDS if name in self.record)
        return next((name for name in present if not isinstance(self.record[name], str)), None)

    @property
    def malformed_ref_field(self) -> str | None:
        present = (name for name in PLAN_REF_FIELDS if name in self.record)
        return next((name for name in present if not is_ref_list(self.record[name])), None)

    def get_shape_problem(self) -> MalformedPlanError | None:
        if (unknown := self.unknown_field) is not None:
            return MalformedPlanError(reason=f'{unknown} is not a plan key')

        if (malformed := self.malformed_text_field) is not None:
            return MalformedPlanError(reason=f'{malformed} must be a string')

        if (malformed := self.malformed_ref_field) is not None:
            return MalformedPlanError(reason=f'{malformed} must be a list of entry refs')

        return None

    def read_refs(self, name: str) -> tuple[str, ...] | None:
        value = self.record.get(name)
        if not isinstance(value, list):
            return None
        return tuple(ref for ref in value if isinstance(ref, str))

    def parse(self) -> Plan:
        return Plan(
            title=read_text(self.record, 'title'),
            goal=read_text(self.record, 'goal'),
            include=self.read_refs('include'),
            blocking=self.read_refs('blocking'),
        )


def load_plan(text: str) -> PlanRecord | MalformedPlanError:
    if not text.strip():
        return PlanRecord(record={})
    try:
        loaded = msgspec.json.decode(text)
    except msgspec.DecodeError as error:
        return MalformedPlanError(reason=f'it is not JSON ({error})')
    if not isinstance(loaded, dict):
        return MalformedPlanError(reason='it is not a JSON object')
    return PlanRecord(record=loaded)
