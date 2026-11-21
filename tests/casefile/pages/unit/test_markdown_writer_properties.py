"""MarkdownWriter: one line per item, in order, with its cite and ref."""

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.views import Document, Item, MarkdownWriter, Section

from tests.casefile.entries.strategies import optional, words


def many[Value](
    strategy: st.SearchStrategy[Value], size: int
) -> st.SearchStrategy[tuple[Value, ...]]:
    return st.builds(tuple, st.lists(strategy, max_size=size))


class TestMarkdownWriterProperties:
    path_cites = st.from_regex(r'[a-z/]{1,10}:[1-9]', fullmatch=True)
    url_cites = st.builds('https://{}'.format, words)
    items = st.builds(
        Item,
        text=words,
        ref=optional(st.from_regex(r'(T[1-9]\.)?e[1-9]', fullmatch=True)),
        cite=optional(st.one_of(path_cites, url_cites)),
        notes=many(words, 2),
        flags=many(words, 2),
    )
    sections = st.builds(Section, title=words, items=many(items, 4), prose=many(words, 2))
    documents = st.builds(Document, title=words, summary=many(words, 2), sections=many(sections, 3))

    @given(document=documents)
    def test_every_item_is_one_line_and_the_lines_follow_the_items_in_order(
        self, document: Document
    ) -> None:
        rendered = MarkdownWriter(document=document).render()

        item_lines = [line for line in rendered.split('\n') if line.startswith('- ')]
        items = [item for section in document.sections for item in section.items]
        assert len(item_lines) == len(items)
        assert all(
            line.startswith(f'- {item.text}') for line, item in zip(item_lines, items, strict=True)
        )
        assert rendered.endswith('\n')

    @given(document=documents)
    def test_an_item_line_ends_with_its_cite_and_ref(self, document: Document) -> None:
        rendered = MarkdownWriter(document=document).render()

        item_lines = [line for line in rendered.split('\n') if line.startswith('- ')]
        items = [item for section in document.sections for item in section.items]
        for line, item in zip(item_lines, items, strict=True):
            assert line.endswith(f' [{item.ref}]') == (item.ref is not None)
            assert (f' <{item.cite}>' in line or f' `{item.cite}`' in line) == (
                item.cite is not None
            )
