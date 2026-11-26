"""Every way a plan is refused, worded as the fix the planner should apply."""

from typing import TYPE_CHECKING

from red_thread_casefile.errors import CaseFileError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from red_thread_plans.domain import Claim, Sentence, TicketDraft

PLAN_KEYS = 'intent, approach, invariants, non_goals, tickets and risks'


class PlanShapeError(CaseFileError):
    def __init__(self, *, reason: str) -> None:
        self.reason = reason
        super().__init__(
            f'the plan cannot be read: {reason}. Send one JSON object with the keys {PLAN_KEYS}.'
        )


class PlanRejectedError(CaseFileError):
    def __init__(self, *, problems: Sequence[CaseFileError]) -> None:
        self.problems = tuple(problems)
        listed = '\n'.join(f'- {problem}' for problem in self.problems)
        super().__init__(
            'no revision was stored. Fix each problem below, then send the whole plan again.\n'
            f'{listed}'
        )


class BlankPlanTextError(CaseFileError):
    def __init__(self, *, field: str) -> None:
        self.field = field
        super().__init__(f'{field} is empty. Write it as a sentence.')


class NoTicketsError(CaseFileError):
    def __init__(self) -> None:
        super().__init__('the plan has no tickets. Cut the work into at least one ticket.')


class MissingAcceptanceError(CaseFileError):
    def __init__(self, *, ticket: str) -> None:
        self.ticket = ticket
        super().__init__(
            f'ticket {ticket} has no acceptance sentence. State at least one outcome someone can '
            'observe when it is done.'
        )


class MissingOwnsError(CaseFileError):
    def __init__(self, *, ticket: str) -> None:
        self.ticket = ticket
        super().__init__(
            f'ticket {ticket} owns no files. List the paths or globs it changes, so its '
            'worktree can be checked against the others.'
        )


class InvalidPlanIdError(CaseFileError):
    def __init__(self, *, field: str, value: str, expected: str) -> None:
        self.field = field
        self.value = value
        self.expected = expected
        super().__init__(f'{field} {value!r} is not {expected}.')


class DuplicatePlanIdError(CaseFileError):
    def __init__(self, *, field: str, value: str) -> None:
        self.field = field
        self.value = value
        super().__init__(f'two {field}s are named {value}. Give each its own id.')


class InvalidOwnedPathError(CaseFileError):
    def __init__(self, *, ticket: str, owned: str, reason: str) -> None:
        self.ticket = ticket
        self.owned = owned
        self.reason = reason
        super().__init__(
            f'ticket {ticket} owns {owned!r}, which {reason}. Write a path from the repository '
            'root, with *, ? and ** as wildcards and dir/ for a whole directory.'
        )


class GroundlessAcceptanceError(CaseFileError):
    def __init__(self, *, sentence: Sentence) -> None:
        self.sentence = sentence
        super().__init__(
            f'{sentence.label} is required by nothing. List in required_by the live decision or '
            'known entries that require it. With none, ask the owner and record the answer first.'
        )


class UnknownRestingRefError(CaseFileError):
    def __init__(self, *, sentence: Sentence, ref: str) -> None:
        self.sentence = sentence
        self.ref = ref
        super().__init__(
            f'{sentence.label} is required by {ref}, which is no entry of the cases the plan '
            'names. Write the case alias, then a ref that render shows, such as C1.e3 or C1.T1.e3.'
        )


class RetiredRestingRefError(CaseFileError):
    def __init__(self, *, sentence: Sentence, ref: str) -> None:
        self.sentence = sentence
        self.ref = ref
        super().__init__(
            f'{sentence.label} is required by {ref}, which a later entry retired. '
            'Rest it on the entry that replaced it.'
        )


class UnfitRestingRefError(CaseFileError):
    def __init__(self, *, sentence: Sentence, ref: str, kind: str) -> None:
        self.sentence = sentence
        self.ref = ref
        self.kind = kind
        super().__init__(
            f'{sentence.label} is required by {ref}, which is a {kind}. Only a decision or a known '
            f'can require a criterion: settle the {kind} first, or ask the owner.'
        )


class UnknownDependencyError(CaseFileError):
    def __init__(self, *, ticket: str, dependency: str) -> None:
        self.ticket = ticket
        self.dependency = dependency
        super().__init__(
            f'ticket {ticket} depends on {dependency}, which is not a ticket in this plan.'
        )


class DependencyCycleError(CaseFileError):
    def __init__(self, *, cycle: Sequence[str]) -> None:
        self.cycle = tuple(cycle)
        arrows = ' -> '.join(self.cycle)
        super().__init__(
            f'the tickets depend on each other in a cycle: {arrows}, where each depends on the '
            'next. Drop one dependency, or merge the tickets.'
        )


class CrossWorktreeDependencyError(CaseFileError):
    def __init__(self, *, ticket: TicketDraft, dependency: TicketDraft) -> None:
        self.ticket = ticket.id
        self.dependency = dependency.id
        super().__init__(
            f'ticket {ticket.id} in worktree {ticket.worktree} depends on {dependency.id} in '
            f'worktree {dependency.worktree}. Tickets that depend on each other share a '
            'worktree: move one.'
        )


class WorktreeCollisionError(CaseFileError):
    def __init__(self, *, first: Claim, second: Claim, example: str) -> None:
        self.first = first
        self.second = second
        self.example = example
        super().__init__(
            f'worktrees {first.worktree} and {second.worktree} can both change {example}: ticket '
            f'{first.ticket} owns {first.owned} and ticket {second.ticket} owns {second.owned}. '
            'Narrow the paths, or put the two tickets in one worktree.'
        )


class UnknownRiskTicketError(CaseFileError):
    def __init__(self, *, risk: str, ticket: str) -> None:
        self.risk = risk
        self.ticket = ticket
        super().__init__(f'risk {risk} names {ticket}, which is not a ticket in this plan.')


class UnlistedCriterionError(CaseFileError):
    def __init__(self, *, risk: str, ticket: str, criterion: str) -> None:
        self.risk = risk
        self.ticket = ticket
        self.criterion = criterion
        super().__init__(
            f'risk {risk} is mitigated by the criterion {criterion!r}, which ticket {ticket} '
            'does not hold. Add it to that ticket as an acceptance sentence.'
        )


class EmptyRecutError(CaseFileError):
    def __init__(self, *, risk: str) -> None:
        self.risk = risk
        super().__init__(
            f'risk {risk} stops work for the owner and names no ticket to cut again. '
            'List those tickets in recut.'
        )


class StrayRecutError(CaseFileError):
    def __init__(self, *, risk: str, ticket: str) -> None:
        self.risk = risk
        self.ticket = ticket
        super().__init__(
            f'risk {risk} would cut {ticket} again, which the risk does not touch. '
            'Add it to the tickets of the risk, or leave it out of recut.'
        )


class CorruptPlanError(CaseFileError):
    def __init__(self, *, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(
            f'{path} is not a plan revision ({reason}). A revision is never edited: '
            'restore it, or remove it and store the plan again.'
        )


class RevisionExistsError(CaseFileError):
    def __init__(self, *, path: Path) -> None:
        self.path = path
        super().__init__(
            f'{path} already exists, and a stored revision is never replaced. '
            'Send the plan again to store it as the next revision.'
        )


class NoCasesError(CaseFileError):
    def __init__(self) -> None:
        super().__init__(
            'the plan names no case. List in cases the investigations it rests on, such as '
            '{"C1": "20261121-retry-queue-slowdown"}.'
        )


class UnknownCaseError(CaseFileError):
    def __init__(self, *, alias: str, case_id: str) -> None:
        self.alias = alias
        self.case_id = case_id
        super().__init__(
            f'case {alias} is {case_id}, which is no case in .red-thread/. '
            'Use the id that init printed for the case.'
        )


class PlanExistsError(CaseFileError):
    def __init__(self, *, plan_id: str) -> None:
        self.plan_id = plan_id
        super().__init__(f'plan {plan_id} already exists. Revise it, or start one with a new slug.')


class MissingPlanError(CaseFileError):
    def __init__(self, *, path: Path) -> None:
        self.path = path
        super().__init__(f'{path} is not a plan. Pass the directory that init printed.')


class NoRevisionError(CaseFileError):
    def __init__(self, *, plan_id: str) -> None:
        self.plan_id = plan_id
        super().__init__(f'plan {plan_id} has no revision yet. Store one with revise first.')
