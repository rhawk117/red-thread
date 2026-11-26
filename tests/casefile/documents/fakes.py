"""A writer that answers each node with the name of the method it reached."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from red_thread_casefile.documents import (
        Code,
        CodeListing,
        EntryList,
        Flowchart,
        Link,
        Paragraph,
        PointList,
        Text,
    )
    from red_thread_casefile.plans.nodes import TicketList


@dataclass(slots=True, kw_only=True, frozen=True)
class NamingWriter:
    def write_text(self, node: Text) -> str:
        return f'text {node.value}'

    def write_code(self, node: Code) -> str:
        return f'code {node.value}'

    def write_link(self, node: Link) -> str:
        return f'link {node.url}'

    def write_paragraph(self, node: Paragraph) -> str:
        return f'paragraph {len(node.line)}'

    def write_entries(self, node: EntryList) -> str:
        return f'entries {len(node.entries)}'

    def write_points(self, node: PointList) -> str:
        return f'points {len(node.points)}'

    def write_flowchart(self, node: Flowchart) -> str:
        return f'flowchart {len(node.lines)}'

    def write_listing(self, node: CodeListing) -> str:
        return f'listing {node.language}'

    def write_tickets(self, node: TicketList) -> str:
        return f'tickets {len(node.tickets)}'
