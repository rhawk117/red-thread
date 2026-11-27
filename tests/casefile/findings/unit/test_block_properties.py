"""Properties of reading finding blocks: one bad block costs only its own finding."""

from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.errors import MalformedBlockError

from tests.casefile.findings.blocks import encode_block, read_case_text, write_blocks_case
from tests.casefile.findings.strategies import words

if TYPE_CHECKING:
    from red_thread_casefile.schemas import CaseReading


def encode_good(text: str) -> str:
    return encode_block({'kind': 'open', 'text': text, 'source': 'scout'})


def encode_bad_kind(text: str) -> str:
    return encode_block({'kind': 'nonsense', 'text': text, 'source': 'scout'})


def encode_unknown_field(text: str) -> str:
    return encode_block({'kind': 'open', 'text': text, 'source': 'scout', 'colour': 'red'})


def read_blocks(blocks: list[str]) -> CaseReading:
    return read_case_text(write_blocks_case(blocks))


class TestBlockProperties:
    good_blocks = st.lists(words.map(encode_good), max_size=5)
    bad_blocks = st.one_of(words.map(encode_bad_kind), words.map(encode_unknown_field))

    @given(before=good_blocks, bad=bad_blocks, after=good_blocks)
    def test_one_bad_block_is_one_fault_at_its_finding_and_the_rest_are_read(
        self, before: list[str], bad: str, after: list[str]
    ) -> None:
        reading = read_blocks([*before, bad, *after])

        bad_finding_id = f'e{len(before) + 1}'
        problems = [p for p in reading.problems if isinstance(p, MalformedBlockError)]
        assert [problem.location.finding_id for problem in problems] == [bad_finding_id]
        assert len(reading.problems) == 1
        assert [finding.finding_id for finding in reading.ledger.findings] == [
            f'e{finding_number}'
            for finding_number in range(1, len(before) + len(after) + 2)
            if f'e{finding_number}' != bad_finding_id
        ]

    @given(good=good_blocks, bad=st.lists(bad_blocks, max_size=4), data=st.data())
    def test_every_block_is_one_finding_or_one_fault(
        self, good: list[str], bad: list[str], data: st.DataObject
    ) -> None:
        blocks = data.draw(st.permutations([*good, *bad]))

        reading = read_blocks(blocks)

        assert len(reading.ledger.findings) == len(good)
        assert len(reading.problems) == len(bad)
