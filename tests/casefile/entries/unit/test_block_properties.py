"""Properties of reading entry blocks: one bad block costs only its own entry."""

from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.errors import MalformedBlockError

from tests.casefile.entries.blocks import encode_block, read_case_text, write_blocks_case
from tests.casefile.entries.strategies import words

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
    def test_one_bad_block_is_one_fault_at_its_entry_and_the_rest_are_read(
        self, before: list[str], bad: str, after: list[str]
    ) -> None:
        reading = read_blocks([*before, bad, *after])

        bad_ref = f'e{len(before) + 1}'
        problems = [p for p in reading.problems if isinstance(p, MalformedBlockError)]
        assert [problem.spot.ref for problem in problems] == [bad_ref]
        assert len(reading.problems) == 1
        assert [entry.ref for entry in reading.ledger.entries] == [
            f'e{seq}' for seq in range(1, len(before) + len(after) + 2) if f'e{seq}' != bad_ref
        ]

    @given(good=good_blocks, bad=st.lists(bad_blocks, max_size=4), data=st.data())
    def test_every_block_is_one_entry_or_one_fault(
        self, good: list[str], bad: list[str], data: st.DataObject
    ) -> None:
        blocks = data.draw(st.permutations([*good, *bad]))

        reading = read_blocks(blocks)

        assert len(reading.ledger.entries) == len(good)
        assert len(reading.problems) == len(bad)
