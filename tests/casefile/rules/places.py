"""Where check names an entry: its file, the line of its heading and its ref."""

from red_thread_casefile.domain import ENTRY_MARK

from tests.casefile.ledger.markdown import name_file


def name_entry_ref(thread: str | None, seq: int) -> str:
    return f'e{seq}' if thread is None else f'{thread}.e{seq}'


def place_entry(text: str, thread: str | None, seq: int) -> str:
    line = text.split('\n').index(f'{ENTRY_MARK}e{seq}') + 1
    return f'{name_file(thread)}:{line} {name_entry_ref(thread, seq)}:'
