"""Every failure the case file reports, worded as the fix the caller should apply."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


def entry_prefix(position: int) -> str:
    return f'entry {position}:'


class CaseFileError(Exception):
    pass


class MalformedBatchError(CaseFileError):
    def __init__(self, *, reason: str) -> None:
        self.reason = reason
        super().__init__(
            f'the batch is not usable: {reason}. '
            'Send a JSON array of entry objects on standard input.'
        )


class UnknownFieldError(CaseFileError):
    def __init__(self, *, position: int, field: str, allowed: Sequence[str]) -> None:
        self.position = position
        self.field = field
        self.allowed = tuple(allowed)
        fields = ', '.join(self.allowed)
        super().__init__(
            f'{entry_prefix(position)} {field} is not an entry field. The fields are {fields}.'
        )


class InvalidFieldError(CaseFileError):
    def __init__(self, *, position: int, field: str, expected: str) -> None:
        self.position = position
        self.field = field
        self.expected = expected
        super().__init__(f'{entry_prefix(position)} {field} must be {expected}.')


class UpgradedVerdictError(CaseFileError):
    def __init__(self, *, position: int, verdict: str) -> None:
        self.position = position
        self.verdict = verdict
        super().__init__(
            f'{entry_prefix(position)} a report with verdict {verdict} cannot be stored as known. '
            'Store it as kind open, and for INFERRED say what it depends on in rests_on.'
        )


class UncitedKnownError(CaseFileError):
    def __init__(self, *, position: int) -> None:
        self.position = position
        super().__init__(
            f'{entry_prefix(position)} a known needs a cite: path:line, a URL or the command that '
            'showed it. Store a claim you cannot cite as kind open.'
        )


class MissingRestsOnError(CaseFileError):
    def __init__(self, *, position: int) -> None:
        self.position = position
        super().__init__(
            f'{entry_prefix(position)} an INFERRED entry needs rests_on, the caveat the inference '
            'depends on, such as "a docs page for another version".'
        )


class DecisionInThreadError(CaseFileError):
    def __init__(self, *, position: int, thread: str) -> None:
        self.position = position
        self.thread = thread
        super().__init__(
            f'{entry_prefix(position)} thread {thread} cannot store a decision. '
            'Return it to the primary as an open question for the owner.'
        )


class DecisionSourceError(CaseFileError):
    def __init__(self, *, position: int, source: str) -> None:
        self.position = position
        self.source = source
        super().__init__(
            f'{entry_prefix(position)} a decision comes only from the owner, and its source is '
            f'{source!r}. Ask the owner, then store the answer with source user.'
        )


class OwnerInThreadError(CaseFileError):
    def __init__(self, *, position: int, thread: str) -> None:
        self.position = position
        self.thread = thread
        super().__init__(
            f'{entry_prefix(position)} thread {thread} cannot store an entry from the owner, '
            'because only the primary talks to the owner. Use your own agent name as source.'
        )


class MissingRefuteError(CaseFileError):
    def __init__(self, *, position: int) -> None:
        self.position = position
        super().__init__(
            f'{entry_prefix(position)} a hypothesis needs refute, the observation that would prove '
            'it wrong.'
        )


class UncitedRuledOutError(CaseFileError):
    def __init__(self, *, position: int) -> None:
        self.position = position
        super().__init__(
            f'{entry_prefix(position)} a ruled_out entry needs a cite, or source user when the '
            'owner ruled it out.'
        )


class UnknownSupersededError(CaseFileError):
    def __init__(self, *, position: int, ref: str) -> None:
        self.position = position
        self.ref = ref
        super().__init__(
            f'{entry_prefix(position)} supersedes names {ref}, which is not in this case. '
            'Use a ref that render shows, such as e3 or T1.e3.'
        )


class ForeignSupersededError(CaseFileError):
    def __init__(self, *, position: int, ref: str, thread: str) -> None:
        self.position = position
        self.ref = ref
        self.thread = thread
        super().__init__(
            f'{entry_prefix(position)} thread {thread} can retire only its own entries, and {ref} '
            'is not one of them. Report the conflict to the primary instead.'
        )


class UnresolvedCiteError(CaseFileError):
    def __init__(self, *, position: int, cite: str) -> None:
        self.position = position
        self.cite = cite
        super().__init__(
            f'{entry_prefix(position)} {cite} does not resolve to a line in this tree. '
            'Open the file and cite a line you read.'
        )


class MisquotedCiteError(CaseFileError):
    def __init__(self, *, position: int, cite: str, found_at: int | None) -> None:
        self.position = position
        self.cite = cite
        self.found_at = found_at
        advice = 'Read the line again, or leave quote out and the line is recorded for you.'
        if found_at is not None:
            advice = f'The quoted text is at line {found_at}; cite that line.'
        super().__init__(f'{entry_prefix(position)} {cite} does not hold the quoted text. {advice}')


class BatchRejectedError(CaseFileError):
    def __init__(self, *, problems: Sequence[CaseFileError]) -> None:
        self.problems = tuple(problems)
        listed = '\n'.join(f'- {problem}' for problem in self.problems)
        super().__init__(
            'nothing was stored. Fix each problem below, then send the whole batch again.\n'
            f'{listed}'
        )


class InvalidThreadError(CaseFileError):
    def __init__(self, *, thread: str) -> None:
        self.thread = thread
        super().__init__(f'{thread!r} is not a thread name. Threads are named T1, T2 and so on.')


class CaseNotFoundError(CaseFileError):
    def __init__(self, *, path: Path) -> None:
        self.path = path
        super().__init__(
            f'{path} is not a case directory, because it has no case.json. '
            'Pass the directory that init printed.'
        )


class CaseExistsError(CaseFileError):
    def __init__(self, *, case_id: str) -> None:
        self.case_id = case_id
        super().__init__(
            f'the case {case_id} already exists. Add to it, or pass --slug to open a new one.'
        )


class CorruptLedgerError(CaseFileError):
    def __init__(self, *, path: Path, line_number: int) -> None:
        self.path = path
        self.line_number = line_number
        super().__init__(
            f'{path} line {line_number} is not a ledger entry. The file is append-only: '
            'remove the broken line by hand, and never edit the lines before it.'
        )


class CorruptCaseError(CaseFileError):
    def __init__(self, *, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(
            f'{path} is not a case record ({reason}). Correct the field it names by hand. '
            'The ledger files beside it are not affected.'
        )


class MalformedPlanError(CaseFileError):
    def __init__(self, *, reason: str) -> None:
        self.reason = reason
        super().__init__(
            f'the plan cannot be read: {reason}. Send one JSON object with any of the keys '
            'title, goal, include and blocking, or send nothing.'
        )


class UnknownPlanRefError(CaseFileError):
    def __init__(self, *, ref: str) -> None:
        self.ref = ref
        super().__init__(
            f'the plan names {ref}, which is not a live entry. '
            'Run render --full and use the refs it shows.'
        )


class LensOverBudgetError(CaseFileError):
    def __init__(self, *, lens: str, lines: int, budget: int) -> None:
        self.lens = lens
        self.lines = lines
        self.budget = budget
        super().__init__(
            f'the {lens} came to {lines} lines and its budget is {budget}, so nothing was '
            'written. Send a plan whose include lists fewer entries, most important first.'
        )


class InvalidTimestampError(CaseFileError):
    def __init__(self, *, timestamp: str) -> None:
        self.timestamp = timestamp
        super().__init__(
            f'{timestamp!r} does not start with a YYYY-MM-DD date. Restore the entry from git, '
            'or record the claim again with add.'
        )


class InvalidPageUrlError(CaseFileError):
    def __init__(self, *, url: str) -> None:
        self.url = url
        super().__init__(
            f'{url!r} is not an https link. Pass the link that publishing the board returned.'
        )


class UnreadableInputError(CaseFileError):
    def __init__(self, *, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(
            f'{path} cannot be read ({reason}). Pass a file that exists, '
            'or leave the option out and send the text on standard input.'
        )
