"""The planner: checks a drafted plan whole against the case, then stores the next revision."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import msgspec

from red_thread_plans.domain import Plan, PlanDraft, Ticket
from red_thread_plans.errors import PlanRejectedError
from red_thread_plans.filters import render_plan_page
from red_thread_plans.page import PlanChanges, PlanPage
from red_thread_plans.policy import PlanPolicy, create_grounds
from red_thread_plans.util import order_stack

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from red_thread_casefile.services.casefile import CaseFile
    from red_thread_core.redaction import SecretPatterns
    from red_thread_core.store import PageStore

    from red_thread_plans.domain import TicketDraft
    from red_thread_plans.store import PlanRepository

PLAN_PAGE = 'plan.html'


@dataclass(slots=True, kw_only=True, frozen=True)
class Scrubbed:
    value: object
    hits: int = 0


@dataclass(slots=True, kw_only=True, frozen=True)
class PlanScrubber:
    patterns: SecretPatterns

    def scrub(self, value: object) -> Scrubbed:
        if isinstance(value, str):
            found = self.patterns.scrub(value)
            return Scrubbed(value=found.text, hits=found.hits)

        if isinstance(value, list):
            items = tuple(map(self.scrub, value))
            return Scrubbed(value=[item.value for item in items], hits=sum_hits(items))

        if isinstance(value, dict):
            fields = {key: self.scrub(item) for key, item in value.items()}
            cleaned = {key: item.value for key, item in fields.items()}
            return Scrubbed(value=cleaned, hits=sum_hits(fields.values()))

        return Scrubbed(value=value)

    def scrub_draft(self, draft: PlanDraft) -> tuple[PlanDraft, int]:
        scrubbed = self.scrub(msgspec.to_builtins(draft))
        return msgspec.convert(scrubbed.value, PlanDraft), scrubbed.hits


def sum_hits(items: Iterable[Scrubbed]) -> int:
    return sum(item.hits for item in items)


def create_ticket(draft: TicketDraft, position: int) -> Ticket:
    return Ticket(
        id=draft.id,
        title=draft.title,
        why=draft.why,
        worktree=draft.worktree,
        position=position,
        acceptance=draft.acceptance,
        owns=draft.owns,
        depends_on=draft.depends_on,
        interface=draft.interface,
    )


@dataclass(slots=True, kw_only=True, frozen=True)
class RevisionStamp:
    revision: int
    at: str
    head: str | None

    def place(self, tickets: tuple[TicketDraft, ...]) -> tuple[Ticket, ...]:
        worktrees = dict.fromkeys(ticket.worktree for ticket in tickets)
        stacks = (
            order_stack([ticket for ticket in tickets if ticket.worktree == worktree])
            for worktree in worktrees
        )
        positions = {name: index for stack in stacks for index, name in enumerate(stack, 1)}
        return tuple(create_ticket(ticket, positions[ticket.id]) for ticket in tickets)

    def apply(self, draft: PlanDraft) -> Plan:
        return Plan(
            revision=self.revision,
            at=self.at,
            head=self.head,
            intent=draft.intent,
            approach=draft.approach,
            invariants=draft.invariants,
            non_goals=draft.non_goals,
            tickets=self.place(draft.tickets),
            risks=draft.risks,
        )


@dataclass(slots=True, kw_only=True, frozen=True)
class Stored:
    plan: Plan
    path: Path
    page: Path
    redactions: int


def find_previous(plans: tuple[Plan, ...], plan: Plan) -> Plan | None:
    earlier = (stored for stored in reversed(plans) if stored.revision < plan.revision)
    return next(earlier, None)


@dataclass(slots=True, kw_only=True, frozen=True)
class Planner:
    record: CaseFile
    plans: PlanRepository
    pages: PageStore

    @property
    def next_revision(self) -> int:
        stored = self.plans.read_plans()
        return stored[-1].revision + 1 if stored else 1

    def propose(self, draft: PlanDraft) -> Stored:
        ledger = self.record.repository.read_ledger()
        policy = PlanPolicy(draft=draft, grounds=create_grounds(ledger))
        if problems := policy.get_plan_issues():
            raise PlanRejectedError(problems=problems)

        clean, hits = PlanScrubber(patterns=self.record.patterns).scrub_draft(draft)
        stamp = RevisionStamp(
            revision=self.next_revision,
            at=self.record.clock.now(),
            head=self.record.tree.get_head(),
        )
        plan = stamp.apply(clean)
        path = self.plans.add(plan)
        return Stored(plan=plan, path=path, page=self.draw(plan), redactions=hits)

    def draw(self, plan: Plan) -> Path:
        changes = PlanChanges(plan=plan, previous=find_previous(self.plans.read_plans(), plan))
        page = PlanPage(case=self.record.repository.read_case(), changes=changes)
        return self.pages.write(PLAN_PAGE, render_plan_page(page.compose()))
