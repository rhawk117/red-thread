"""The failures of a whole case and of the commands that read it."""

from typing import TYPE_CHECKING

from red_thread_casefile.errors.base import CaseFileError

if TYPE_CHECKING:
    from pathlib import Path


class CaseNotFoundError(CaseFileError):
    def __init__(self, *, path: Path) -> None:
        self.path = path
        super().__init__(
            f'{path} is not a case directory, because it has no case.md. '
            'Pass the directory that init printed.'
        )


class CaseExistsError(CaseFileError):
    def __init__(self, *, case_id: str) -> None:
        self.case_id = case_id
        super().__init__(
            f'the case {case_id} already exists. Write to its case.md, or pass --slug to open '
            'a new one.'
        )


class MalformedSelectionError(CaseFileError):
    def __init__(self, *, reason: str) -> None:
        self.reason = reason
        super().__init__(
            f'the selection cannot be read: {reason}. Send one JSON object with any of the keys '
            'title, goal, include and blocking, or send nothing.'
        )


class UnknownSelectedFindingError(CaseFileError):
    def __init__(self, *, finding_id: str) -> None:
        self.finding_id = finding_id
        super().__init__(
            f'the selection names {finding_id}, which is not a live finding. '
            'Run render --full and use the finding ids it shows.'
        )


class LensOverBudgetError(CaseFileError):
    def __init__(self, *, lens: str, lines: int, budget: int) -> None:
        self.lens = lens
        self.lines = lines
        self.budget = budget
        super().__init__(
            f'the {lens} came to {lines} lines and its budget is {budget}, so nothing was '
            'written. Send a selection whose include lists fewer findings, most important first.'
        )


class InvalidTimestampError(CaseFileError):
    def __init__(self, *, timestamp: str) -> None:
        self.timestamp = timestamp
        super().__init__(
            f'{timestamp!r} does not start with a YYYY-MM-DD date. Correct the created key in '
            'the frontmatter of case.md.'
        )


class InvalidPageUrlError(CaseFileError):
    def __init__(self, *, url: str) -> None:
        self.url = url
        super().__init__(
            f'case.md: page_url {url!r} is not an https link. Write the link that publishing '
            'the board returned.'
        )


class UnreadableInputError(CaseFileError):
    def __init__(self, *, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(
            f'{path} cannot be read ({reason}). Pass a file that exists, '
            'or leave the option out and send the text on standard input.'
        )
