"""Reads exported Markdown the way a caller would: headings, items, finding ids and remarks."""

import re

FINDING_ID_BUTTON = re.compile(r'\[((?:T[1-9]\d*\.)?e[1-9]\d*)\]$')
TRAILING_CITE = re.compile(r' (?:`[^`]*`|<[^>]*>)$')
HEADING_MARK = '## '
ITEM_MARK = '- '


def list_headings(text: str) -> list[str]:
    lines = (line for line in text.splitlines() if line.startswith(HEADING_MARK))
    return [line.removeprefix(HEADING_MARK) for line in lines]


def list_section_lines(text: str, title: str) -> list[str]:
    section: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.startswith(HEADING_MARK):
            inside = line.removeprefix(HEADING_MARK) == title

        if inside and line.strip() and not line.startswith(HEADING_MARK):
            section.append(line)
    return section


def read_finding_id(line: str) -> str | None:
    found = FINDING_ID_BUTTON.search(line)
    return found[1] if found else None


def list_finding_ids(text: str, title: str) -> list[str]:
    finding_ids = (read_finding_id(line) for line in list_section_lines(text, title))
    return [finding_id for finding_id in finding_ids if finding_id is not None]


def list_all_finding_ids(text: str) -> list[str]:
    finding_ids = (
        read_finding_id(line) for line in text.splitlines() if line.startswith(ITEM_MARK)
    )
    return [finding_id for finding_id in finding_ids if finding_id is not None]


def find_item(text: str, finding_id: str) -> str:
    return next(line for line in text.splitlines() if read_finding_id(line) == finding_id)


def list_remarks(line: str) -> list[str]:
    unreffed = FINDING_ID_BUTTON.sub('', line).rstrip()
    uncited = TRAILING_CITE.sub('', unreffed)
    if not uncited.endswith(')'):
        return []
    inner = uncited[uncited.rindex('(') + 1 : -1]
    return inner.split('; ')
