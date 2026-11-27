"""The faults check finds in one finding, each worded as the fix to apply."""

from typing import TYPE_CHECKING

from red_thread_casefile.errors.base import CaseFileError, name_place

if TYPE_CHECKING:
    from red_thread_casefile.domain import FindingLocation


class UpgradedVerdictError(CaseFileError):
    def __init__(self, *, location: FindingLocation, verdict: str) -> None:
        self.location = location
        self.verdict = verdict
        super().__init__(
            f'{name_place(location)} a report with verdict {verdict} cannot be recorded as known. '
            'Make it kind open, and for INFERRED say what it depends on in rests_on.'
        )


class UncitedKnownError(CaseFileError):
    def __init__(self, *, location: FindingLocation) -> None:
        self.location = location
        super().__init__(
            f'{name_place(location)} a known needs a cite: path:line, a URL or the command that '
            'showed it. Make a claim you cannot cite kind open.'
        )


class MissingRestsOnError(CaseFileError):
    def __init__(self, *, location: FindingLocation) -> None:
        self.location = location
        super().__init__(
            f'{name_place(location)} an INFERRED finding needs rests_on, the caveat the inference '
            'depends on, such as "a docs page for another version".'
        )


class DecisionInThreadError(CaseFileError):
    def __init__(self, *, location: FindingLocation, thread: str) -> None:
        self.location = location
        self.thread = thread
        super().__init__(
            f'{name_place(location)} thread {thread} cannot hold a decision. '
            'Return it to the primary as an open question for the owner.'
        )


class DecisionSourceError(CaseFileError):
    def __init__(self, *, location: FindingLocation, source: str) -> None:
        self.location = location
        self.source = source
        super().__init__(
            f'{name_place(location)} a decision comes only from the owner, and its source is '
            f'{source!r}. Ask the owner, then record the answer with source user.'
        )


class OwnerInThreadError(CaseFileError):
    def __init__(self, *, location: FindingLocation, thread: str) -> None:
        self.location = location
        self.thread = thread
        super().__init__(
            f'{name_place(location)} thread {thread} cannot hold a finding from the owner, '
            'because only the primary talks to the owner. Use your own agent name as source.'
        )


class MissingRefuteError(CaseFileError):
    def __init__(self, *, location: FindingLocation) -> None:
        self.location = location
        super().__init__(
            f'{name_place(location)} a hypothesis needs refute, the observation that would prove '
            'it wrong.'
        )


class UncitedRuledOutError(CaseFileError):
    def __init__(self, *, location: FindingLocation) -> None:
        self.location = location
        super().__init__(
            f'{name_place(location)} a ruled_out finding needs a cite, or source user when the '
            'owner ruled it out.'
        )


class UnknownSupersededError(CaseFileError):
    def __init__(self, *, location: FindingLocation, finding_id: str) -> None:
        self.location = location
        self.finding_id = finding_id
        super().__init__(
            f'{name_place(location)} supersedes names {finding_id}, which is not in this case. '
            'Use a finding id that render shows, such as e3 or T1.e3.'
        )


class ForeignSupersededError(CaseFileError):
    def __init__(self, *, location: FindingLocation, finding_id: str, thread: str) -> None:
        self.location = location
        self.finding_id = finding_id
        self.thread = thread
        super().__init__(
            f'{name_place(location)} thread {thread} can retire only its own findings, '
            f'and {finding_id} is not one of them. Report the conflict to the primary instead.'
        )


class UnresolvedCitationError(CaseFileError):
    def __init__(self, *, location: FindingLocation, citation: str) -> None:
        self.location = location
        self.citation = citation
        super().__init__(
            f'{name_place(location)} {citation} does not resolve to a line in this tree. '
            'Open the file and cite a line you read.'
        )


class MisquotedCitationError(CaseFileError):
    def __init__(self, *, location: FindingLocation, citation: str, found_at: int | None) -> None:
        self.location = location
        self.citation = citation
        self.found_at = found_at
        advice = 'Read the line again and copy it into quote exactly.'
        if found_at is not None:
            advice = f'The quoted text is at line {found_at}; cite that line.'
        super().__init__(
            f'{name_place(location)} {citation} does not hold the quoted text. {advice}'
        )


class MissingQuoteError(CaseFileError):
    def __init__(self, *, location: FindingLocation, citation: str, line: str) -> None:
        self.location = location
        self.citation = citation
        self.line = line
        super().__init__(
            f'{name_place(location)} {citation} has no quote, so a later check cannot tell a moved '
            f'line from a changed one. Add quote with the cited line, which reads: {line}'
        )


class SecretInFindingError(CaseFileError):
    def __init__(self, *, location: FindingLocation, field: str, scrubbed: str) -> None:
        self.location = location
        self.field = field
        self.scrubbed = scrubbed
        super().__init__(
            f'{name_place(location)} {field} holds what looks like a secret. Replace the value '
            f'with: {scrubbed}'
        )
