"""Entry blocks written by hand into a case file, for reading one block's fields back."""

from typing import TYPE_CHECKING

import msgspec
from red_thread_casefile.domain import CASE_FILE, LedgerSource
from red_thread_casefile.schemas import read_case_file

from tests.casefile.ledger.builders import create_case
from tests.casefile.ledger.markdown import write_case_text

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from red_thread_casefile.domain import RoundStamp
    from red_thread_casefile.schemas import CaseReading

ROUND = '## Round 1 · 2026-11-21 · none\n'


def encode_block(fields: Mapping[str, object]) -> str:
    return msgspec.yaml.encode(fields).decode()


def write_block_entry(seq: int, block: str) -> str:
    return f'### e{seq}\n\n```yaml\n{block}```\n'


def write_entries(first: int, records: Sequence[Mapping[str, object]]) -> str:
    blocks = map(encode_block, records)
    return '\n'.join(write_block_entry(seq, block) for seq, block in enumerate(blocks, first))


def write_round(stamp: RoundStamp, first: int, records: Sequence[Mapping[str, object]]) -> str:
    return f'{stamp.heading}\n\n{write_entries(first, records)}'


def write_blocks_case(blocks: Sequence[str]) -> str:
    entries = (write_block_entry(seq, block) for seq, block in enumerate(blocks, 1))
    return '\n'.join((write_case_text(create_case()), ROUND, *entries))


def read_case_text(text: str) -> CaseReading:
    return read_case_file([LedgerSource(name=CASE_FILE, thread=None, text=text)])
