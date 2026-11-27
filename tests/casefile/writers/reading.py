"""Renders a document through a writer and picks out the lines a test reads."""

from functools import cache
from typing import TYPE_CHECKING

from red_thread_casefile.packaged import load_wording
from red_thread_casefile.writers.page import create_case_page_writer
from red_thread_core.documents import parse_line
from red_thread_core.writers.markdown import MarkdownWriter

if TYPE_CHECKING:
    from jinja2 import Environment
    from red_thread_casefile.writers.page import CasePageWriter
    from red_thread_core.documents import Document

LINE_TEMPLATE = "{% import 'macros.html.j2' as draw %}{{ draw.line(line) }}"


@cache
def load_case_page_writer() -> CasePageWriter:
    return create_case_page_writer(load_wording().headings)


def load_page_environment() -> Environment:
    return load_case_page_writer().writer.environment


def render_markdown(document: Document) -> str:
    return MarkdownWriter(document=document).render()


def render_page(document: Document) -> str:
    return load_case_page_writer().render(document)


def render_marked_up(text: str) -> str:
    return load_page_environment().from_string(LINE_TEMPLATE).render(line=parse_line(text))


def list_item_lines(document: Document) -> list[str]:
    return [line for line in render_markdown(document).splitlines() if line.startswith('- ')]
