"""Renders a document through a writer and picks out the lines a test reads."""

from typing import TYPE_CHECKING

from red_thread_casefile.writers.markdown import MarkdownWriter

if TYPE_CHECKING:
    from red_thread_casefile.documents import Document


def render_markdown(document: Document) -> str:
    return MarkdownWriter(document=document).render()


def list_item_lines(document: Document) -> list[str]:
    return [line for line in render_markdown(document).splitlines() if line.startswith('- ')]
