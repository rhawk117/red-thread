"""A ticket's plan: the frontmatter the scripts read and write, and the parts of its body."""

import re
from dataclasses import dataclass
from datetime import date
from itertools import chain
from typing import TYPE_CHECKING, Literal

import msgspec
from red_thread_core.dto import DTO

if TYPE_CHECKING:
    from red_thread_casefile.domain import EntryKind

type Status = Literal['draft', 'accepted', 'done']
type Lights = Literal['on', 'off']

TICKET_HOME = 'tickets'
PLAN_FILE = 'plan.md'
FENCE = '---'
HEADING = '## '
ITEM = '- '
RESTING_KINDS: tuple[EntryKind, ...] = ('decision', 'known')
SETTLED: tuple[Status, ...] = ('accepted', 'done')
REF = re.compile(r'\bC[1-9]\d*\.(?:T[1-9]\d*\.)?e[1-9]\d*\b')
ACCEPTANCE = 'Acceptance'


class Outline(DTO, frozen=True, kw_only=True, forbid_unknown_fields=True, gc=False):
    sections: tuple[str, ...]
    required: tuple[str, ...]


class Frontmatter(DTO, frozen=True, kw_only=True, forbid_unknown_fields=True, gc=False):
    id: str
    title: str
    status: Status = 'draft'
    revision: int = 1
    created: date
    head: str | None = None
    cases: dict[str, str] = msgspec.field(default_factory=dict)
    lights: Lights | None = None
    epic: str | None = None
    issue: str | None = None


@dataclass(slots=True, kw_only=True, frozen=True)
class BodyLine:
    number: int
    text: str

    @property
    def is_item(self) -> bool:
        return self.text.startswith(ITEM)

    @property
    def refs(self) -> tuple[str, ...]:
        return tuple(match.group() for match in REF.finditer(self.text))


@dataclass(slots=True, kw_only=True, frozen=True)
class Section:
    title: str
    number: int
    lines: tuple[BodyLine, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not any(line.text.strip() for line in self.lines)

    @property
    def items(self) -> tuple[BodyLine, ...]:
        return tuple(line for line in self.lines if line.is_item)


@dataclass(slots=True, kw_only=True, frozen=True)
class PlanDocument:
    frontmatter: Frontmatter
    sections: tuple[Section, ...] = ()

    def find_section(self, title: str) -> Section | None:
        return next((section for section in self.sections if section.title == title), None)

    @property
    def lines(self) -> tuple[BodyLine, ...]:
        return tuple(chain.from_iterable(section.lines for section in self.sections))

    @property
    def criteria(self) -> tuple[BodyLine, ...]:
        acceptance = self.find_section(ACCEPTANCE)
        return () if acceptance is None else acceptance.items


@dataclass(slots=True, kw_only=True, frozen=True)
class Opening:
    id: str
    title: str
    case_ids: tuple[str, ...]
