"""One page writer for the core tests, built once, and the page and the blocks drawn through it."""

from functools import cache
from typing import TYPE_CHECKING

from red_thread_core.writers.page import HtmlPage, create_page_writer

if TYPE_CHECKING:
    from red_thread_core.documents import Block, Document
    from red_thread_core.writers.page import ChipRow, PageWriter


@cache
def load_page_writer() -> PageWriter:
    return create_page_writer()


def render_core_page(document: Document, filters: tuple[ChipRow, ...] = ()) -> str:
    return load_page_writer().render(HtmlPage(document=document, filters=filters))


def render_block(block: Block) -> str:
    return load_page_writer().environment.get_template(block.template).render(block=block)
