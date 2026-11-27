"""HTML built step by step: each call returns a new element, and render escapes every value."""

import re
from html import escape
from itertools import pairwise
from typing import TYPE_CHECKING

from red_thread_core.dto import DTO

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

type AttributeValue = str | int | bool | None
type Attribute = tuple[str, AttributeValue]
type ElementChild = Element | str

INDENT = '  '
INLINE_TAGS = frozenset({'a', 'button', 'code', 'em', 'span', 'strong', 'time'})
PREFORMATTED_TAGS = frozenset({'pre'})
URL_ATTRIBUTES = frozenset({'href', 'src'})
SAFE_SCHEMES = frozenset({'', 'http', 'https'})
URL_SCHEME = re.compile(r'[a-z][a-z0-9+.-]*(?=:)', re.IGNORECASE)
URL_IGNORED_CHARACTERS = re.compile(r'[\t\n\r]')
C0_AND_SPACE = ''.join(map(chr, range(0x21)))


def find_scheme(url: str) -> str:
    found = URL_SCHEME.match(URL_IGNORED_CHARACTERS.sub('', url).lstrip(C0_AND_SPACE))
    return found.group().lower() if found else ''


def blank_unsafe_url(url: str) -> str:
    return url if find_scheme(url) in SAFE_SCHEMES else ''


def is_rendered_attribute(attribute: Attribute) -> bool:
    _, value = attribute
    return value is not None and value is not False


def write_attribute(attribute: Attribute) -> str:
    name, value = attribute
    if value is True:
        return f' {name}'
    rendered_value = blank_unsafe_url(str(value)) if name in URL_ATTRIBUTES else str(value)
    return f' {name}="{escape(rendered_value)}"'


def is_inline(child: ElementChild) -> bool:
    return isinstance(child, str) or child.tag in INLINE_TAGS


def are_both_inline(pair: tuple[ElementChild, ElementChild]) -> bool:
    first, second = pair
    return is_inline(first) and is_inline(second)


def render_inline(child: ElementChild) -> str:
    if isinstance(child, str):
        return escape(child)
    return child.render_inline()


def render_child_line(child: ElementChild, depth: int) -> str:
    if isinstance(child, str):
        return escape(child)
    return child.render(depth)


class Element(DTO, frozen=True, kw_only=True, gc=False):
    tag: str
    attributes: tuple[Attribute, ...] = ()
    children: tuple[ElementChild, ...] = ()

    def with_attributes(self, attributes: Mapping[str, AttributeValue]) -> Element:
        return self.replace_with(attributes=(*self.attributes, *attributes.items()))

    def nest(self, *children: ElementChild | None) -> Element:
        kept = tuple(child for child in children if child is not None)
        return self.replace_with(children=(*self.children, *kept))

    def set_text(self, text: object) -> Element:
        return self.replace_with(children=(str(text),))

    @property
    def opening_tag(self) -> str:
        written = ''.join(map(write_attribute, filter(is_rendered_attribute, self.attributes)))
        return f'<{self.tag}{written}>'

    @property
    def closing_tag(self) -> str:
        return f'</{self.tag}>'

    @property
    def has_text_child(self) -> bool:
        return any(isinstance(child, str) for child in self.children)

    @property
    def has_inline_children(self) -> bool:
        children = self.children
        return all(map(is_inline, children)) or any(map(are_both_inline, pairwise(children)))

    @property
    def stays_on_one_line(self) -> bool:
        if self.tag in PREFORMATTED_TAGS or not self.children:
            return True
        return self.has_text_child or self.has_inline_children

    def render_inline(self) -> str:
        return f'{self.opening_tag}{"".join(map(render_inline, self.children))}{self.closing_tag}'

    def render(self, depth: int = 0) -> str:
        if self.stays_on_one_line:
            return self.render_inline()
        inner = INDENT * (depth + 1)
        lines = (f'{inner}{render_child_line(child, depth + 1)}' for child in self.children)
        return '\n'.join((self.opening_tag, *lines, f'{INDENT * depth}{self.closing_tag}'))


def element(tag: str) -> Element:
    return Element(tag=tag)


def render_fragment(elements: Iterable[Element | None]) -> str:
    return ''.join(f'{child.render()}\n' for child in elements if child is not None)
