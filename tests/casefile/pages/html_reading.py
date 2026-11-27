"""Reads a page the way a browser would: elements, attributes, code spans, chips and entry refs."""

import re
from dataclasses import dataclass
from html import unescape

TAILWIND_URL = 'https://cdnjs.cloudflare.com/ajax/libs/tailwindcss-browser/4.3.5/index.global.js'
MERMAID_URL = 'https://cdnjs.cloudflare.com/ajax/libs/mermaid/12.3.0/mermaid.min.js'
ATTRIBUTE_RUN = r'((?:\s+[\w:-]+(?:="[^"]*")?)*)'
TAG = re.compile(rf'<([A-Za-z][A-Za-z0-9]*){ATTRIBUTE_RUN}\s*>')
TAG_START = re.compile(r'<[A-Za-z]')
ATTRIBUTE = re.compile(r'([\w:-]+)(?:="([^"]*)")?')
CODE_BODY = re.compile(r'(<(script|style)\b[^>]*>).*?(</\2>)', re.DOTALL)
SCRIPT_ELEMENT = re.compile(rf'<script{ATTRIBUTE_RUN}\s*>(.*?)</script>', re.DOTALL)
STYLE_ELEMENT = re.compile(rf'<style{ATTRIBUTE_RUN}\s*>(.*?)</style>', re.DOTALL)
CHIP = re.compile(rf'<button{ATTRIBUTE_RUN}\s*>([^<]*)<span class="count">(\d+)</span></button>')
CHIP_GROUP = re.compile(r'<div class="chips"[^>]*>(.*?)</div>', re.DOTALL)
CODE_SPAN = re.compile(r'<code>(.*?)</code>', re.DOTALL)
ITEM_REF = re.compile(r'<button type="button" class="ref"[^>]*>(.*?)</button>', re.DOTALL)
FLAG = re.compile(r'<li class="flag">(.*?)</li>')
MERMAID = re.compile(r'<pre class="mermaid">(.*?)</pre>', re.DOTALL)
SECTION_HEAD = re.compile(r'<summary>\s*<h2>(.*?)</h2>', re.DOTALL)
CLAIM = re.compile(r'<p class="claim">(.*?)</p>', re.DOTALL)
FACT = re.compile(
    r'<div class="(fact(?: wide)?)">\s*<dt>(.*?)</dt>\s*<dd>(.*?)</dd>\s*</div>', re.DOTALL
)
FACT_LINK = re.compile(r'<a href="([^"]*)" rel="noreferrer">')
SECTION = re.compile(
    rf'<details{ATTRIBUTE_RUN}\s*>\s*<summary>\s*<h2>(.*?)</h2>'
    r'(?:\s*<span class="count">(\d+)</span>)?(?:\s*<span class="about">(.*?)</span>)?'
    r'\s*</summary>(.*?)</details>',
    re.DOTALL,
)
SPAN = re.compile(rf'<span{ATTRIBUTE_RUN}\s*>([^<]*)</span>')
QUOTE = re.compile(r'<pre class="quote"><code>(.*?)</code></pre>', re.DOTALL)
CITED_QUOTE = re.compile(
    r'<p class="cite">(?:(?!</p>).)*</p>\s*<pre class="quote"><code>(.*?)</code></pre>', re.DOTALL
)
NOTE_LIST = re.compile(r'<ul class="notes">(.*?)</ul>', re.DOTALL)
NOTE_ROW = re.compile(r'<li(?: class="(\w+)")?>(.*?)</li>', re.DOTALL)
ANY_TAG = re.compile(r'<[^>]*>')
LAYOUT_BREAK = re.compile(r'>\n\s*<')
CITE_BLOCK = re.compile(r'<p class="cite">(.*?)</p>', re.DOTALL)
PAGE_TAGS = frozenset({
    'html',
    'head',
    'meta',
    'title',
    'style',
    'script',
    'body',
    'main',
    'aside',
    'header',
    'h1',
    'h2',
    'ul',
    'ol',
    'dl',
    'dt',
    'dd',
    'time',
    'li',
    'details',
    'summary',
    'nav',
    'button',
    'pre',
    'p',
    'span',
    'div',
    'code',
    'a',
    'del',
    'ins',
})


@dataclass(slots=True, kw_only=True, frozen=True)
class Element:
    attributes: dict[str, str]
    body: str


@dataclass(slots=True, kw_only=True, frozen=True)
class ChipReading:
    group: str
    value: str
    label: str
    count: int


@dataclass(slots=True, kw_only=True, frozen=True)
class FactReading:
    label: str
    value: str
    wide: bool
    link: str | None


@dataclass(slots=True, kw_only=True, frozen=True)
class SectionReading:
    attributes: dict[str, str]
    title: str
    count: int | None
    note: str | None
    body: str


def join_layout(page: str) -> str:
    return LAYOUT_BREAK.sub('><', page)


def read_all(pattern: re.Pattern[str], page: str) -> list[str]:
    return list(map(unescape, pattern.findall(page)))


def read_attributes(text: str) -> dict[str, str]:
    return {name: unescape(value) for name, value in ATTRIBUTE.findall(text)}


def list_tags(page: str) -> list[tuple[str, dict[str, str]]]:
    markup = CODE_BODY.sub(r'\1\3', page)
    tags = [(found[1].lower(), read_attributes(found[2])) for found in TAG.finditer(markup)]
    assert len(tags) == len(TAG_START.findall(markup)), 'markup the page did not close as a tag'
    return tags


def list_tag_names(page: str) -> set[str]:
    return {name for name, _ in list_tags(page)}


def list_attribute_names(page: str) -> set[str]:
    return {attribute for _, attributes in list_tags(page) for attribute in attributes}


def find_tags(page: str, name: str) -> list[dict[str, str]]:
    return [attributes for tag, attributes in list_tags(page) if tag == name]


def find_outbound_links(page: str) -> list[dict[str, str]]:
    return [link for link in find_tags(page, 'a') if not link['href'].startswith('#')]


def find_buttons(page: str, role: str) -> list[dict[str, str]]:
    return [button for button in find_tags(page, 'button') if button.get('class') == role]


def find_entries(page: str) -> list[dict[str, str]]:
    return [item for item in find_tags(page, 'li') if item.get('class') == 'entry']


def list_scripts(page: str) -> list[Element]:
    found = SCRIPT_ELEMENT.findall(page)
    return [Element(attributes=read_attributes(run), body=body) for run, body in found]


def list_styles(page: str) -> list[Element]:
    found = STYLE_ELEMENT.findall(page)
    return [Element(attributes=read_attributes(run), body=body) for run, body in found]


def read_chips(markup: str) -> list[ChipReading]:
    found = [(read_attributes(run), label, count) for run, label, count in CHIP.findall(markup)]
    return [
        ChipReading(
            group=attributes['data-filter'],
            value=attributes['data-value'],
            label=unescape(label).removesuffix(' '),
            count=int(count),
        )
        for attributes, label, count in found
        if attributes.get('class') == 'chip'
    ]


def list_chip_groups(page: str) -> list[list[ChipReading]]:
    return [read_chips(group) for group in CHIP_GROUP.findall(page)]


def list_copy_values(page: str) -> list[str]:
    return [
        attributes['data-copy'] for _, attributes in list_tags(page) if 'data-copy' in attributes
    ]


def list_mermaid(page: str) -> list[str]:
    return read_all(MERMAID, page)


def list_section_titles(page: str) -> list[str]:
    return read_all(SECTION_HEAD, page)


def list_cite_blocks(page: str) -> list[str]:
    return CITE_BLOCK.findall(page)


def list_claims(page: str) -> list[str]:
    return [unescape(TAG.sub('', claim)) for claim in CLAIM.findall(page)]


def list_code_spans(page: str) -> list[str]:
    return read_all(CODE_SPAN, page)


def list_item_refs(page: str) -> list[str]:
    return read_all(ITEM_REF, page)


def list_flags(page: str) -> list[str]:
    return read_all(FLAG, page)


def list_facts(page: str) -> list[FactReading]:
    return [
        FactReading(
            label=unescape(label),
            value=unescape(ANY_TAG.sub('', value)),
            wide=style == 'fact wide',
            link=unescape(link[1]) if (link := FACT_LINK.search(value)) else None,
        )
        for style, label, value in FACT.findall(page)
    ]


def list_sections(page: str) -> list[SectionReading]:
    return [
        SectionReading(
            attributes=read_attributes(run),
            title=unescape(title),
            count=int(count) if count else None,
            note=unescape(note) if note else None,
            body=body,
        )
        for run, title, count, note, body in SECTION.findall(page)
    ]


def list_spans(page: str, role: str) -> list[Element]:
    found = [(read_attributes(run), unescape(body)) for run, body in SPAN.findall(page)]
    return [
        Element(attributes=attributes, body=body)
        for attributes, body in found
        if attributes.get('class') == role
    ]


def list_quotes(page: str) -> list[str]:
    return read_all(QUOTE, page)


def list_cited_quotes(page: str) -> list[str]:
    return read_all(CITED_QUOTE, page)


def list_claim_markup(page: str) -> list[str]:
    return CLAIM.findall(page)


def list_note_rows(page: str) -> list[list[tuple[str, str]]]:
    return [
        [(role, unescape(ANY_TAG.sub('', text))) for role, text in NOTE_ROW.findall(block)]
        for block in NOTE_LIST.findall(page)
    ]
