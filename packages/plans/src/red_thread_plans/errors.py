"""Every way a plan is refused, worded as the fix to apply."""

from typing import TYPE_CHECKING

from red_thread_core.errors import RedThreadError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from red_thread_casefile.domain import EntryKind

FIELDS = 'id, title, status, revision, created, head, cases, lights, epic and issue'


class PlanError(RedThreadError):
    pass


class PlanShapeError(PlanError):
    def __init__(self, *, reason: str, hint: str | None = None) -> None:
        self.reason = reason
        self.hint = hint
        fix = hint or f'Keep the frontmatter that init wrote: the keys {FIELDS}'
        super().__init__(f'the plan cannot be read: {reason}. {fix}.')


class PlanRejectedError(PlanError):
    def __init__(self, *, problems: Sequence[PlanError]) -> None:
        self.problems = tuple(problems)
        listed = '\n'.join(f'- {problem}' for problem in self.problems)
        super().__init__(
            f'the plan is not sound. Fix each problem below, then check again.\n{listed}'
        )


class PlanExistsError(PlanError):
    def __init__(self, *, path: Path) -> None:
        self.path = path
        super().__init__(f'{path} already exists. Edit it, or give init another --slug.')


class MissingPlanError(PlanError):
    def __init__(self, *, path: Path) -> None:
        self.path = path
        super().__init__(f'there is no plan at {path}. Pass the plan.md that init printed.')


class NoCasesError(PlanError):
    def __init__(self) -> None:
        super().__init__(
            'the plan names no case. Pass --case once for each case under .red-thread/ it rests on.'
        )


class UnknownCaseError(PlanError):
    def __init__(self, *, alias: str | None, case_id: str) -> None:
        self.alias = alias
        self.case_id = case_id
        named = case_id if alias is None else f'{alias} ({case_id})'
        super().__init__(
            f'case {named} is not under .red-thread/. Name a case directory that exists there.'
        )


class MissingSectionError(PlanError):
    def __init__(self, *, title: str) -> None:
        self.title = title
        super().__init__(f'the plan has no "## {title}" section. Put the heading back.')


class EmptySectionError(PlanError):
    def __init__(self, *, title: str, line: int) -> None:
        self.title = title
        self.line = line
        super().__init__(f'line {line}: "## {title}" is empty. Write it before checking.')


class NoCriteriaError(PlanError):
    def __init__(self, *, line: int) -> None:
        self.line = line
        super().__init__(
            f'line {line}: "## Acceptance" has no criterion. Write each as a line that starts'
            ' with "- ".'
        )


class GroundlessCriterionError(PlanError):
    def __init__(self, *, line: int) -> None:
        self.line = line
        super().__init__(
            f'line {line}: this criterion names no entry. End it with the refs of the decision or'
            ' known entries that require it, such as (C1.e4, C1.e2).'
        )


class UnknownRefError(PlanError):
    def __init__(self, *, line: int, ref: str) -> None:
        self.line = line
        self.ref = ref
        super().__init__(f'line {line}: {ref} is not an entry of its case. Check the ref.')


class RetiredRefError(PlanError):
    def __init__(self, *, line: int, ref: str) -> None:
        self.line = line
        self.ref = ref
        super().__init__(
            f'line {line}: {ref} was retired by a later entry. Name the entry that replaced it.'
        )


class UnfitRefError(PlanError):
    def __init__(self, *, line: int, ref: str, kind: EntryKind) -> None:
        self.line = line
        self.ref = ref
        self.kind = kind
        super().__init__(
            f'line {line}: {ref} is a {kind} entry, and a criterion rests only on a decision or a'
            ' known. Record what the owner decided or a scout verified, then name that.'
        )


class UnsetLightsError(PlanError):
    def __init__(self, *, status: str) -> None:
        self.status = status
        super().__init__(
            f'the plan is {status} and lights is not set. Ask the owner whether the lights are on'
            ' or off, and write their answer.'
        )
