"""The faults that stop a case file from being read: its frontmatter, headings and blocks."""

from typing import TYPE_CHECKING

from red_thread_casefile.errors.base import CaseFileError, name_place

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from red_thread_casefile.domain import FindingLocation

FINDING_FIELDS = (
    'kind, text, source, verdict, cite, quote, addr, rests_on, refute, diagram, supersedes'
)


class UndecodableFileError(CaseFileError):
    def __init__(self, *, path: Path) -> None:
        self.path = path
        super().__init__(
            f'{path} is not UTF-8 text, so it cannot be read. Write the file again as UTF-8.'
        )


class MalformedFrontmatterError(CaseFileError):
    def __init__(self, *, file: str, reason: str) -> None:
        self.file = file
        self.reason = reason
        super().__init__(
            f'{file}: the frontmatter cannot be read: {reason}. It sits between the --- lines '
            'at the top; correct the key the reason names.'
        )


class MalformedRoundError(CaseFileError):
    def __init__(self, *, location: FindingLocation) -> None:
        self.location = location
        super().__init__(
            f'{name_place(location)} this is not a round heading. Write ## Round N · YYYY-MM-DD · '
            'HEAD, with the date from date -u +%F and HEAD from git rev-parse --short HEAD, '
            'or none outside git.'
        )


class MalformedFindingHeadingError(CaseFileError):
    def __init__(self, *, location: FindingLocation) -> None:
        self.location = location
        super().__init__(
            f'{name_place(location)} this is not a finding heading. Write ### e and the next '
            'number in this file, such as ### e4.'
        )


class FindingBeforeRoundError(CaseFileError):
    def __init__(self, *, location: FindingLocation) -> None:
        self.location = location
        super().__init__(
            f'{name_place(location)} this finding comes before any round heading. Write '
            '## Round N · YYYY-MM-DD · HEAD above it.'
        )


class StrayTextError(CaseFileError):
    def __init__(self, *, location: FindingLocation) -> None:
        self.location = location
        super().__init__(
            f"{name_place(location)} this text is outside a finding's yaml block, so nothing reads "
            'it. Move it into the text of a finding, or delete it.'
        )


class MissingBlockError(CaseFileError):
    def __init__(self, *, location: FindingLocation) -> None:
        self.location = location
        super().__init__(
            f'{name_place(location)} this finding has no yaml block. Under its heading, open a '
            'fence with ```yaml, write the fields, and close it with ```.'
        )


class MalformedBlockError(CaseFileError):
    def __init__(self, *, location: FindingLocation, reason: str) -> None:
        self.location = location
        self.reason = reason
        super().__init__(
            f'{name_place(location)} the yaml block cannot be read: {reason}. The fields are '
            f'{FINDING_FIELDS}. Write a value that holds ": " or " #", or starts with a quote '
            'mark or a bracket, as a block: the key, then |-, then the value indented on the '
            'next line.'
        )


class NumberingError(CaseFileError):
    def __init__(self, *, location: FindingLocation, expected: int) -> None:
        self.location = location
        self.expected = expected
        super().__init__(
            f'{name_place(location)} this finding should be e{expected}. Findings in one file are '
            'numbered e1, e2 and so on, in order, with no gap and no repeat.'
        )


class RoundOrderError(CaseFileError):
    def __init__(self, *, location: FindingLocation, number: int, previous: int) -> None:
        self.location = location
        self.number = number
        self.previous = previous
        super().__init__(
            f'{name_place(location)} this is round {number}, but the round heading above it is '
            f'round {previous}. Rounds in one file go up, with one heading each: delete this '
            f'heading if its findings belong to round {previous}, or number it above {previous}.'
        )


class StrayThreadFileError(CaseFileError):
    def __init__(self, *, file: str) -> None:
        self.file = file
        super().__init__(
            f'{file} is not a thread file, so nothing reads it. Thread files are named '
            'threads/T1.md, threads/T2.md and so on.'
        )


class MalformedCaseError(CaseFileError):
    def __init__(self, *, problems: Sequence[CaseFileError]) -> None:
        self.problems = tuple(problems)
        listed = '\n'.join(f'- {problem}' for problem in self.problems)
        super().__init__(
            f'the case file cannot be read. Fix each fault below, then run check.\n{listed}'
        )
