"""Finding blocks written by hand into a case file, for reading one block's fields back."""

from typing import TYPE_CHECKING

from red_thread_casefile.domain import CASE_FILE, LedgerSource

from tests.casefile.ledger.builders import create_case
from tests.casefile.ledger.markdown import SCHEMA, write_case_text
from tests.codec import YAML

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from red_thread_casefile.domain import RoundStamp
    from red_thread_casefile.schemas import CaseReading

ROUND = '## Round 1 · 2026-11-21 · none\n'


def encode_block(fields: Mapping[str, object]) -> str:
    return YAML.encode_text(fields)


def write_block_finding(finding_number: int, block: str) -> str:
    return f'### e{finding_number}\n\n```yaml\n{block}```\n'


def write_findings(first: int, records: Sequence[Mapping[str, object]]) -> str:
    blocks = map(encode_block, records)
    return '\n'.join(
        write_block_finding(finding_number, block)
        for finding_number, block in enumerate(blocks, first)
    )


def write_round(stamp: RoundStamp, first: int, records: Sequence[Mapping[str, object]]) -> str:
    return f'{stamp.heading}\n\n{write_findings(first, records)}'


def write_blocks_case(blocks: Sequence[str]) -> str:
    findings = (
        write_block_finding(finding_number, block) for finding_number, block in enumerate(blocks, 1)
    )
    return '\n'.join((write_case_text(create_case()), ROUND, *findings))


def read_case_text(text: str) -> CaseReading:
    return SCHEMA.read([LedgerSource(name=CASE_FILE, thread=None, text=text)])
