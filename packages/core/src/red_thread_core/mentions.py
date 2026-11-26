"""The plans that cite a case, read at draw time from each plan's index beside the cases."""

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from red_thread_core.places import PLAN_INDEX

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(slots=True, kw_only=True, frozen=True)
class PlanMention:
    id: str
    title: str
    cases: tuple[str, ...]

    def cites(self, case_id: str) -> bool:
        return case_id in self.cases


@runtime_checkable
class MentionShelf(Protocol):
    def list_mentions(self, case_id: str) -> tuple[PlanMention, ...]: ...


def is_text_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def read_mention(text: str) -> PlanMention | None:
    try:
        found = json.loads(text)
    except ValueError:
        return None

    if not isinstance(found, dict):
        return None

    plan_id, title, cases = found.get('id'), found.get('title'), found.get('cases', [])
    if not isinstance(plan_id, str) or not isinstance(title, str) or not is_text_list(cases):
        return None

    return PlanMention(id=plan_id, title=title, cases=tuple(cases))


@dataclass(slots=True, kw_only=True, frozen=True)
class MemoryMentionShelf:
    mentions: tuple[PlanMention, ...] = field(default_factory=tuple)

    def list_mentions(self, case_id: str) -> tuple[PlanMention, ...]:
        return tuple(mention for mention in self.mentions if mention.cites(case_id))


def read_index(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except OSError, UnicodeDecodeError:
        return ''


@dataclass(slots=True, kw_only=True, frozen=True)
class DirectoryMentionShelf:
    directory: Path

    def read_all(self) -> tuple[PlanMention, ...]:
        paths = sorted(self.directory.glob(f'*/{PLAN_INDEX}'))
        found = (read_mention(read_index(path)) for path in paths)
        return tuple(mention for mention in found if mention is not None)

    def list_mentions(self, case_id: str) -> tuple[PlanMention, ...]:
        return MemoryMentionShelf(mentions=self.read_all()).list_mentions(case_id)
