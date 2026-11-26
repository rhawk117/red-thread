"""The faults check finds in one entry, each worded as the fix to apply."""

from typing import TYPE_CHECKING

from red_thread_casefile.errors.base import CaseFileError, name_place

if TYPE_CHECKING:
    from red_thread_casefile.domain import Spot


class UpgradedVerdictError(CaseFileError):
    def __init__(self, *, spot: Spot, verdict: str) -> None:
        self.spot = spot
        self.verdict = verdict
        super().__init__(
            f'{name_place(spot)} a report with verdict {verdict} cannot be recorded as known. '
            'Make it kind open, and for INFERRED say what it depends on in rests_on.'
        )


class UncitedKnownError(CaseFileError):
    def __init__(self, *, spot: Spot) -> None:
        self.spot = spot
        super().__init__(
            f'{name_place(spot)} a known needs a cite: path:line, a URL or the command that '
            'showed it. Make a claim you cannot cite kind open.'
        )


class MissingRestsOnError(CaseFileError):
    def __init__(self, *, spot: Spot) -> None:
        self.spot = spot
        super().__init__(
            f'{name_place(spot)} an INFERRED entry needs rests_on, the caveat the inference '
            'depends on, such as "a docs page for another version".'
        )


class DecisionInThreadError(CaseFileError):
    def __init__(self, *, spot: Spot, thread: str) -> None:
        self.spot = spot
        self.thread = thread
        super().__init__(
            f'{name_place(spot)} thread {thread} cannot hold a decision. '
            'Return it to the primary as an open question for the owner.'
        )


class DecisionSourceError(CaseFileError):
    def __init__(self, *, spot: Spot, source: str) -> None:
        self.spot = spot
        self.source = source
        super().__init__(
            f'{name_place(spot)} a decision comes only from the owner, and its source is '
            f'{source!r}. Ask the owner, then record the answer with source user.'
        )


class OwnerInThreadError(CaseFileError):
    def __init__(self, *, spot: Spot, thread: str) -> None:
        self.spot = spot
        self.thread = thread
        super().__init__(
            f'{name_place(spot)} thread {thread} cannot hold an entry from the owner, '
            'because only the primary talks to the owner. Use your own agent name as source.'
        )


class MissingRefuteError(CaseFileError):
    def __init__(self, *, spot: Spot) -> None:
        self.spot = spot
        super().__init__(
            f'{name_place(spot)} a hypothesis needs refute, the observation that would prove '
            'it wrong.'
        )


class UncitedRuledOutError(CaseFileError):
    def __init__(self, *, spot: Spot) -> None:
        self.spot = spot
        super().__init__(
            f'{name_place(spot)} a ruled_out entry needs a cite, or source user when the '
            'owner ruled it out.'
        )


class UnknownSupersededError(CaseFileError):
    def __init__(self, *, spot: Spot, ref: str) -> None:
        self.spot = spot
        self.ref = ref
        super().__init__(
            f'{name_place(spot)} supersedes names {ref}, which is not in this case. '
            'Use a ref that render shows, such as e3 or T1.e3.'
        )


class ForeignSupersededError(CaseFileError):
    def __init__(self, *, spot: Spot, ref: str, thread: str) -> None:
        self.spot = spot
        self.ref = ref
        self.thread = thread
        super().__init__(
            f'{name_place(spot)} thread {thread} can retire only its own entries, and {ref} '
            'is not one of them. Report the conflict to the primary instead.'
        )


class UnresolvedCiteError(CaseFileError):
    def __init__(self, *, spot: Spot, cite: str) -> None:
        self.spot = spot
        self.cite = cite
        super().__init__(
            f'{name_place(spot)} {cite} does not resolve to a line in this tree. '
            'Open the file and cite a line you read.'
        )


class MisquotedCiteError(CaseFileError):
    def __init__(self, *, spot: Spot, cite: str, found_at: int | None) -> None:
        self.spot = spot
        self.cite = cite
        self.found_at = found_at
        advice = 'Read the line again and copy it into quote exactly.'
        if found_at is not None:
            advice = f'The quoted text is at line {found_at}; cite that line.'
        super().__init__(f'{name_place(spot)} {cite} does not hold the quoted text. {advice}')


class MissingQuoteError(CaseFileError):
    def __init__(self, *, spot: Spot, cite: str, line: str) -> None:
        self.spot = spot
        self.cite = cite
        self.line = line
        super().__init__(
            f'{name_place(spot)} {cite} has no quote, so a later check cannot tell a moved line '
            f'from a changed one. Add quote with the cited line, which reads: {line}'
        )


class SecretInEntryError(CaseFileError):
    def __init__(self, *, spot: Spot, field: str, scrubbed: str) -> None:
        self.spot = spot
        self.field = field
        self.scrubbed = scrubbed
        super().__init__(
            f'{name_place(spot)} {field} holds what looks like a secret. Replace the value '
            f'with: {scrubbed}'
        )
