"""A document as one page: a rail of what the page is, beside its sections in columns."""

from dataclasses import dataclass
from itertools import groupby
from operator import attrgetter
from typing import TYPE_CHECKING

from red_thread_core.writers.markup import create_page_environment

if TYPE_CHECKING:
    from collections.abc import Iterable

    from jinja2 import Environment

    from red_thread_core.documents import Document, Section

MIN_CHIPS = 2
MIN_CONTENTS = 2
PAGE_TEMPLATE = 'page.html.j2'


@dataclass(slots=True, kw_only=True, frozen=True)
class Chip:
    group: str
    value: str
    label: str
    count: int


type ChipRow = tuple[Chip, ...]


@dataclass(slots=True, kw_only=True, frozen=True)
class SectionGroup:
    column: bool
    sections: tuple[Section, ...]


def create_group(group: tuple[bool, Iterable[Section]]) -> SectionGroup:
    column, sections = group
    return SectionGroup(column=column, sections=tuple(sections))


def is_shown_row(chips: ChipRow) -> bool:
    return len(chips) >= MIN_CHIPS


@dataclass(slots=True, kw_only=True, frozen=True)
class HtmlPage:
    document: Document
    filters: tuple[ChipRow, ...] = ()

    @property
    def sections(self) -> tuple[Section, ...]:
        return (*self.document.sections, *self.document.appendix)

    @property
    def groups(self) -> tuple[SectionGroup, ...]:
        return tuple(map(create_group, groupby(self.sections, key=attrgetter('column'))))

    @property
    def chip_rows(self) -> tuple[ChipRow, ...]:
        return tuple(filter(is_shown_row, self.filters))

    @property
    def has_contents(self) -> bool:
        return len(self.sections) >= MIN_CONTENTS


@dataclass(slots=True, kw_only=True, frozen=True)
class PageWriter:
    environment: Environment

    def render(self, page: HtmlPage) -> str:
        return self.environment.get_template(PAGE_TEMPLATE).render(page=page)


def create_page_writer(*packages: str) -> PageWriter:
    return PageWriter(environment=create_page_environment(*packages))
