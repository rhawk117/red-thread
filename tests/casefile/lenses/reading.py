"""Reads an exported Markdown output the way a caller would: headings, items, refs and remarks."""

import re

ITEM_REF = re.compile(r'\[((?:T[1-9]\d*\.)?e[1-9]\d*)\]$')
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


def read_ref(line: str) -> str | None:
    found = ITEM_REF.search(line)
    return found[1] if found else None


def list_refs(text: str, title: str) -> list[str]:
    refs = (read_ref(line) for line in list_section_lines(text, title))
    return [ref for ref in refs if ref is not None]


def list_all_refs(text: str) -> list[str]:
    refs = (read_ref(line) for line in text.splitlines() if line.startswith(ITEM_MARK))
    return [ref for ref in refs if ref is not None]


def find_item(text: str, ref: str) -> str:
    return next(line for line in text.splitlines() if read_ref(line) == ref)


def list_remarks(line: str) -> list[str]:
    unreffed = ITEM_REF.sub('', line).rstrip()
    uncited = TRAILING_CITE.sub('', unreffed)
    if not uncited.endswith(')'):
        return []
    inner = uncited[uncited.rindex('(') + 1 : -1]
    return inner.split('; ')
