"""What every rendered page promises: its own scripts and styles, and only the writer's elements."""

from red_thread_casefile.assets import read_asset

from tests.casefile.pages.html_reading import (
    MERMAID_URL,
    PAGE_TAGS,
    TAILWIND_URL,
    list_scripts,
    list_styles,
    list_tags,
)

TAILWIND_STYLE = 'text/tailwindcss'


def assert_page_holds_only_its_own_markup(page: str) -> None:
    tags = list_tags(page)
    assert {name for name, _ in tags} <= PAGE_TAGS
    assert not [name for _, attributes in tags for name in attributes if name.startswith('on')]
    assert [name for name, attributes in tags if 'src' in attributes] == ['script', 'script']
    assert {name for name, attributes in tags if 'href' in attributes} <= {'a'}

    scripts = list_scripts(page)
    sources = sorted(script.attributes.get('src', '') for script in scripts)
    assert sources == sorted(['', TAILWIND_URL, MERMAID_URL])
    inline = next(script for script in scripts if 'src' not in script.attributes)
    assert inline.body.strip() == read_asset('page.js').strip()

    styles = {style.attributes.get('type', ''): style.body.strip() for style in list_styles(page)}
    assert len(list_styles(page)) == len(styles) == 2
    assert styles == {
        '': read_asset('page.css').strip(),
        TAILWIND_STYLE: read_asset('tailwind.css').strip(),
    }
