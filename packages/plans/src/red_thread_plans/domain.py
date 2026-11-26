"""The plan record as drafted on standard input and as stored, one revision per file."""

import re
from dataclasses import dataclass
from operator import attrgetter
from typing import TYPE_CHECKING, Literal

import msgspec

if TYPE_CHECKING:
    from collections.abc import Iterable

    from red_thread_casefile.domain import Case, EntryKind, Ledger

type PlanSchema = Literal['red-thread/plan@1']
type IndexSchema = Literal['red-thread/plan-index@1']
type Handling = Accept | Mitigate | YouIntervene

PLAN_SCHEMA: PlanSchema = 'red-thread/plan@1'
INDEX_SCHEMA: IndexSchema = 'red-thread/plan-index@1'
RESTING_KINDS: tuple[EntryKind, ...] = ('decision', 'known')
SLUG = re.compile(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*')
RISK_ID = re.compile(r'R[1-9]\d*')
CASE_ALIAS = re.compile(r'C[1-9]\d*')


class Interface(msgspec.Struct, frozen=True, kw_only=True, forbid_unknown_fields=True, gc=False):
    language: str
    source: str


class Acceptance(msgspec.Struct, frozen=True, kw_only=True, forbid_unknown_fields=True, gc=False):
    criterion: str
    required_by: tuple[str, ...] = ()


class Accept(
    msgspec.Struct,
    frozen=True,
    kw_only=True,
    forbid_unknown_fields=True,
    gc=False,
    tag='accept',
    tag_field='kind',
):
    pass


class Mitigate(
    msgspec.Struct,
    frozen=True,
    kw_only=True,
    forbid_unknown_fields=True,
    gc=False,
    tag='mitigate',
    tag_field='kind',
):
    ticket: str
    criterion: str | None = None


class YouIntervene(
    msgspec.Struct,
    frozen=True,
    kw_only=True,
    forbid_unknown_fields=True,
    gc=False,
    tag='you-intervene',
    tag_field='kind',
):
    recut: tuple[str, ...] = ()


class Risk(msgspec.Struct, frozen=True, kw_only=True, forbid_unknown_fields=True, gc=False):
    id: str
    risk: str
    signal: str
    handling: Handling
    tickets: tuple[str, ...] = ()


class TicketDraft(msgspec.Struct, frozen=True, kw_only=True, forbid_unknown_fields=True, gc=False):
    id: str
    title: str
    why: str
    worktree: str
    acceptance: tuple[Acceptance, ...] = ()
    owns: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    interface: Interface | None = None


class PlanDraft(msgspec.Struct, frozen=True, kw_only=True, forbid_unknown_fields=True, gc=False):
    intent: str
    approach: str
    cases: dict[str, str] = msgspec.field(default_factory=dict)
    invariants: tuple[str, ...] = ()
    non_goals: tuple[str, ...] = ()
    tickets: tuple[TicketDraft, ...] = ()
    risks: tuple[Risk, ...] = ()


class Ticket(msgspec.Struct, frozen=True, kw_only=True, forbid_unknown_fields=True, gc=False):
    id: str
    title: str
    why: str
    worktree: str
    position: int
    acceptance: tuple[Acceptance, ...] = ()
    owns: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    interface: Interface | None = None


class Plan(msgspec.Struct, frozen=True, kw_only=True, forbid_unknown_fields=True, gc=False):
    revision: int
    at: str
    head: str | None
    intent: str
    approach: str
    schema: PlanSchema = PLAN_SCHEMA
    cases: dict[str, str] = msgspec.field(default_factory=dict)
    invariants: tuple[str, ...] = ()
    non_goals: tuple[str, ...] = ()
    tickets: tuple[Ticket, ...] = ()
    risks: tuple[Risk, ...] = ()

    @property
    def worktrees(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(ticket.worktree for ticket in self.tickets))

    def stack(self, worktree: str) -> tuple[Ticket, ...]:
        in_worktree = (ticket for ticket in self.tickets if ticket.worktree == worktree)
        return tuple(sorted(in_worktree, key=attrgetter('position')))

    def find_ticket(self, ticket_id: str) -> Ticket | None:
        return next((ticket for ticket in self.tickets if ticket.id == ticket_id), None)


class IssueLink(msgspec.Struct, frozen=True, kw_only=True, forbid_unknown_fields=True, gc=False):
    ticket: str
    url: str


class PlanIndex(msgspec.Struct, frozen=True, kw_only=True, forbid_unknown_fields=True, gc=False):
    id: str
    title: str
    at: str
    schema: IndexSchema = INDEX_SCHEMA
    cases: tuple[str, ...] = ()
    epic: str | None = None
    issues: tuple[IssueLink, ...] = ()

    def find_issue(self, ticket_id: str) -> str | None:
        return next((link.url for link in self.issues if link.ticket == ticket_id), None)


def cite_cases(index: PlanIndex, case_ids: Iterable[str]) -> PlanIndex:
    return msgspec.structs.replace(index, cases=tuple(dict.fromkeys((*index.cases, *case_ids))))


@dataclass(slots=True, kw_only=True, frozen=True)
class Opening:
    id: str
    title: str


@dataclass(slots=True, kw_only=True, frozen=True)
class CaseRecord:
    case: Case
    ledger: Ledger


@dataclass(slots=True, kw_only=True, frozen=True)
class Sentence:
    ticket: str
    number: int

    @property
    def label(self) -> str:
        return f'ticket {self.ticket}, acceptance {self.number}'


@dataclass(slots=True, kw_only=True, frozen=True)
class Claim:
    worktree: str
    ticket: str
    owned: str
