"""The contract between a plan's stored index and the board that lists the plans citing it."""

from hypothesis import given
from hypothesis import strategies as st
from red_thread_core.mentions import PlanMention, read_mention
from red_thread_plans.domain import PlanIndex
from red_thread_plans.schemas import to_text


class TestIndexAsMention:
    indexes = st.builds(
        PlanIndex,
        id=st.text(),
        title=st.text(),
        at=st.just('2026-11-26T10:00:00+00:00'),
        cases=st.lists(st.text()).map(tuple),
        epic=st.none() | st.just('https://example.invalid/epic/1'),
    )

    @given(index=indexes)
    def test_every_stored_index_reads_as_a_mention_of_its_cases(self, index: PlanIndex) -> None:
        mention = PlanMention(id=index.id, title=index.title, cases=index.cases)

        assert read_mention(to_text(index)) == mention
