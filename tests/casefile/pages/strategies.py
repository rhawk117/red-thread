"""Strategies for page documents: text that holds no backtick and sequences of any strategy."""

from hypothesis import strategies as st

texts = st.text(
    alphabet=st.characters(blacklist_categories=('Cs',), blacklist_characters='`'), max_size=30
)


def many[Value](
    strategy: st.SearchStrategy[Value], size: int
) -> st.SearchStrategy[tuple[Value, ...]]:
    return st.builds(tuple, st.lists(strategy, max_size=size))
