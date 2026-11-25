"""Renders a document through a writer and picks out the lines a test reads."""

from typing import TYPE_CHECKING

from red_thread_casefile.documents import parse_line
from red_thread_casefile.writers.markdown import MarkdownWriter
from red_thread_casefile.writers.markup import HtmlInlines, render_value
from red_thread_casefile.writers.page import HtmlPage

if TYPE_CHECKING:
    from red_thread_casefile.documents import Document


def render_markdown(document: Document) -> str:
    return MarkdownWriter(document=document).render()


def render_page(document: Document) -> str:
    return HtmlPage(document=document).render()


def render_marked_up(text: str) -> str:
    return render_value(HtmlInlines().write_line(parse_line(text)))


def list_item_lines(document: Document) -> list[str]:
    return [line for line in render_markdown(document).splitlines() if line.startswith('- ')]
