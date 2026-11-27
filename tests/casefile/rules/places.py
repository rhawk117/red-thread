"""Where check names a finding: its file, the line of its heading and its finding id."""

from red_thread_casefile.domain import FINDING_MARK

from tests.casefile.ledger.markdown import name_file


def name_finding_id(thread: str | None, finding_number: int) -> str:
    return f'e{finding_number}' if thread is None else f'{thread}.e{finding_number}'


def place_finding(text: str, thread: str | None, finding_number: int) -> str:
    line = text.split('\n').index(f'{FINDING_MARK}e{finding_number}') + 1
    return f'{name_file(thread)}:{line} {name_finding_id(thread, finding_number)}:'
