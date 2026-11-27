"""The core blocks: each one is a Block, counts nothing, and writes both HTML and Markdown."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_core.documents import (
    Block,
    CodeListing,
    Flowchart,
    Paragraph,
    PointList,
    Section,
    parse_line,
)

from tests.params import as_labelled_params

if TYPE_CHECKING:
    from red_thread_core.elements import Element


def core_block_cases() -> pytest.MarkDecorator:
    blocks: dict[str, Block] = {
        'paragraph': Paragraph(line=parse_line('a `b`')),
        'points': PointList(points=(parse_line('a'), parse_line('b'))),
        'flowchart': Flowchart(lines=('flowchart TD', '  A --> B')),
        'listing': CodeListing(language='python', source='def a() -> None: ...'),
    }
    return pytest.mark.parametrize('block', as_labelled_params(blocks))


@dataclass(slots=True, kw_only=True, frozen=True)
class CountedBlock:
    count: int

    def write_html(self) -> Element | None:
        return None

    def write_markdown(self) -> tuple[str, ...]:
        return ()


class TestCoreBlocks:
    @core_block_cases()
    def test_a_core_block_is_a_block(self, block: Block) -> None:
        assert isinstance(block, Block)

    @core_block_cases()
    def test_a_core_block_counts_nothing(self, block: Block) -> None:
        assert block.count == 0

    @core_block_cases()
    def test_a_core_block_writes_html_and_markdown(self, block: Block) -> None:
        assert block.write_html()
        assert block.write_markdown()

    def test_a_listing_writes_a_fence_named_for_its_language(self) -> None:
        listing = CodeListing(language='python', source='a\nb')

        assert listing.write_markdown() == ('```python', 'a', 'b', '```')


class TestSectionCount:
    counts = st.lists(st.integers(min_value=0, max_value=50), max_size=6)

    @given(counts=counts)
    def test_a_section_counts_what_its_blocks_count(self, counts: list[int]) -> None:
        section = Section(title='t', blocks=tuple(CountedBlock(count=count) for count in counts))

        assert section.count == sum(counts)
