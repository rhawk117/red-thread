"""Reads the lines of a case map: its subgraphs, nodes, links and retirements."""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

SUBGRAPH = re.compile(r'subgraph\s+(\S+)\["(.*)"\]')
NODE = re.compile(r'(n\d+)\["(.*)"\]:::(k_\w+)')
LINK = re.compile(r'(n\d+) --- (n\d+)')
RETIREMENT = re.compile(r'(n\d+) -\. retires \.-> (n\d+)')
PATTERNS = (SUBGRAPH, NODE, LINK, RETIREMENT)
LABEL_CHARACTERS = re.compile(r"[\w .,:/()+='-]*")


@dataclass(slots=True, kw_only=True, frozen=True)
class NodeReading:
    name: str
    label: str
    style: str
    thread_title: str


@dataclass(slots=True, kw_only=True, frozen=True)
class MapReading:
    subgraph_ids: tuple[str, ...]
    titles: tuple[str, ...]
    nodes: tuple[NodeReading, ...]
    links: tuple[tuple[str, str], ...]
    retirements: tuple[tuple[str, str], ...]
    strays: tuple[str, ...]


def read_map(lines: Iterable[str]) -> MapReading:
    stripped = [line.strip() for line in lines]
    ids: list[str] = []
    titles: list[str] = []
    nodes: list[NodeReading] = []
    links: list[tuple[str, str]] = []
    retirements: list[tuple[str, str]] = []
    title = ''
    for line in stripped:
        if found := SUBGRAPH.fullmatch(line):
            title = found[2]
            ids.append(found[1])
            titles.append(title)

        if found := NODE.fullmatch(line):
            nodes.append(
                NodeReading(name=found[1], label=found[2], style=found[3], thread_title=title)
            )

        if found := LINK.fullmatch(line):
            links.append((found[1], found[2]))

        if found := RETIREMENT.fullmatch(line):
            retirements.append((found[1], found[2]))

    strays = [
        line
        for line in stripped
        if line != 'end' and not any(pattern.fullmatch(line) for pattern in PATTERNS)
    ]
    return MapReading(
        subgraph_ids=tuple(ids),
        titles=tuple(titles),
        nodes=tuple(nodes),
        links=tuple(links),
        retirements=tuple(retirements),
        strays=tuple(strays),
    )
