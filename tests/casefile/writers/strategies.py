"""Document trees drawn by Hypothesis, for the writer properties."""

from hypothesis import strategies as st
from red_thread_casefile.documents import CitationNode, FindingList, FindingNode, Note
from red_thread_core.documents import Document, Paragraph, PointList, Section, parse_line

from tests.casefile.documents.builders import MOMENT
from tests.casefile.findings.strategies import optional, words


def many[Value](
    strategy: st.SearchStrategy[Value], size: int
) -> st.SearchStrategy[tuple[Value, ...]]:
    return st.builds(tuple, st.lists(strategy, max_size=size))


path_citations = st.from_regex(r'[a-z/]{1,10}:[1-9]', fullmatch=True)
url_citations = st.builds('https://{}'.format, words)
citations = st.builds(CitationNode, target=st.one_of(path_citations, url_citations))
lines = st.builds(parse_line, words)
notes = st.builds(Note, kind=st.sampled_from(('rests_on', 'source', 'urgency')), text=words)
findings = st.builds(
    FindingNode,
    finding_id=st.from_regex(r'(T[1-9]\.)?e[1-9]', fullmatch=True),
    kind=st.just('known'),
    claim=lines,
    round=st.integers(min_value=1, max_value=9),
    at=st.just(MOMENT),
    citation_node=optional(citations),
    notes=many(notes, 2),
    lead=optional(st.just('1111111')),
)
blocks = st.one_of(
    st.builds(Paragraph, line=lines),
    st.builds(FindingList, findings=many(findings, 4)),
    st.builds(PointList, points=many(lines, 3)),
)
sections = st.builds(Section, title=words, blocks=many(blocks, 3))
documents = st.builds(Document, title=words, summary=many(lines, 2), sections=many(sections, 3))
