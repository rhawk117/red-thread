"""HTML built step by step: each call returns a new element, and render escapes every value."""

import re
from dataclasses import dataclass, replace
from html import escape
from itertools import pairwise
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

type AttributeValue = str | int | bool | None
type Attribute = tuple[str, AttributeValue]
type Node = Element | str

INDENT = '  '
PHRASING_TAGS = frozenset({'a', 'button', 'code', 'em', 'span', 'strong', 'time'})
PRESERVED_TAGS = frozenset({'pre'})
URL_ATTRIBUTES = frozenset({'href', 'src'})
SAFE_SCHEMES = frozenset({'', 'http', 'https'})
URL_SCHEME = re.compile(r'[a-z][a-z0-9+.-]*(?=:)', re.IGNORECASE)
URL_NOISE = re.compile(r'[\t\n\r]')
C0_AND_SPACE = ''.join(map(chr, range(0x21)))


def find_scheme(url: str) -> str:
    found = URL_SCHEME.match(URL_NOISE.sub('', url).lstrip(C0_AND_SPACE))
    return found.group().lower() if found else ''


def keep_safe_url(url: str) -> str:
    return url if find_scheme(url) in SAFE_SCHEMES else ''


def is_written(attribute: Attribute) -> bool:
    _, value = attribute
    return value is not None and value is not False


def write_attribute(attribute: Attribute) -> str:
    name, value = attribute
    if value is True:
        return f' {name}'
    shown = keep_safe_url(str(value)) if name in URL_ATTRIBUTES else str(value)
    return f' {name}="{escape(shown)}"'


def is_phrasing(node: Node) -> bool:
    return isinstance(node, str) or node.tag in PHRASING_TAGS


def are_phrasing(pair: tuple[Node, Node]) -> bool:
    first, second = pair
    return is_phrasing(first) and is_phrasing(second)


def render_inline(node: Node) -> str:
    if isinstance(node, str):
        return escape(node)
    return node.render_inline()


def render_nested(node: Node, depth: int) -> str:
    if isinstance(node, str):
        return escape(node)
    return node.render(depth)


@dataclass(slots=True, kw_only=True, frozen=True)
class Element:
    tag: str
    attrs: tuple[Attribute, ...] = ()
    children: tuple[Node, ...] = ()

    def attributes(self, attrs: Mapping[str, AttributeValue]) -> Element:
        return replace(self, attrs=(*self.attrs, *attrs.items()))

    def nest(self, *children: Node | None) -> Element:
        kept = tuple(child for child in children if child is not None)
        return replace(self, children=(*self.children, *kept))

    def set_text(self, text: object) -> Element:
        return replace(self, children=(str(text),))

    @property
    def opening(self) -> str:
        written = ''.join(map(write_attribute, filter(is_written, self.attrs)))
        return f'<{self.tag}{written}>'

    @property
    def closing(self) -> str:
        return f'</{self.tag}>'

    @property
    def holds_text(self) -> bool:
        return any(isinstance(child, str) for child in self.children)

    @property
    def runs_inline(self) -> bool:
        children = self.children
        return all(map(is_phrasing, children)) or any(map(are_phrasing, pairwise(children)))

    @property
    def stays_on_one_line(self) -> bool:
        if self.tag in PRESERVED_TAGS or not self.children:
            return True
        return self.holds_text or self.runs_inline

    def render_inline(self) -> str:
        return f'{self.opening}{"".join(map(render_inline, self.children))}{self.closing}'

    def render(self, depth: int = 0) -> str:
        if self.stays_on_one_line:
            return self.render_inline()
        inner = INDENT * (depth + 1)
        lines = (f'{inner}{render_nested(child, depth + 1)}' for child in self.children)
        return '\n'.join((self.opening, *lines, f'{INDENT * depth}{self.closing}'))


def element(tag: str) -> Element:
    return Element(tag=tag)


def render_fragment(nodes: Iterable[Element | None]) -> str:
    return ''.join(f'{node.render()}\n' for node in nodes if node is not None)
