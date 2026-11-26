"""A writer that answers each inline node with the name of the method it reached."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from red_thread_core.documents import Code, Link, Text


@dataclass(slots=True, kw_only=True, frozen=True)
class NamingWriter:
    def write_text(self, node: Text) -> str:
        return f'text {node.value}'

    def write_code(self, node: Code) -> str:
        return f'code {node.value}'

    def write_link(self, node: Link) -> str:
        return f'link {node.url}'
