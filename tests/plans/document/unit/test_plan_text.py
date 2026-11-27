"""Plan text both ways: init's skeleton reads back whole, and a broken frontmatter says why."""

import string
from dataclasses import dataclass

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_plans.domain import Frontmatter, PlanDocument, find_cited_finding_ids
from red_thread_plans.errors import PlanShapeError
from red_thread_plans.packaged import load_outline
from red_thread_plans.schemas import LIGHTS_HINT, read_plan, write_plan

from tests.codec import YAML
from tests.params import as_params
from tests.plans.document.builders import (
    CASE_LINE,
    CRITERION,
    edit_plan,
    find_line_number,
    write_sound_plan,
)

CASE_ID = '20261121-retry-queue-slowdown'


@dataclass(slots=True, kw_only=True, frozen=True)
class ShapeFault:
    name: str
    edits: tuple[tuple[str, str], ...]
    hint: str | None = None
    marks: tuple[pytest.MarkDecorator, ...] = ()


def plan_shape_fault_cases() -> pytest.MarkDecorator:
    unopened = ShapeFault(name='no-opening-fence', edits=(('---\n', ''),))
    unclosed = ShapeFault(name='no-closing-fence', edits=(('---\n\n#', '\n#'),))
    stray = ShapeFault(name='unknown-key', edits=(('status:', 'owner: me\nstatus:'),))
    bare = ShapeFault(name='bare-lights', edits=(('lights: null', 'lights: on'),), hint=LIGHTS_HINT)
    return pytest.mark.parametrize('fault', as_params((unopened, unclosed, stray, bare)))


def read_sound_plan() -> PlanDocument:
    document = read_plan(YAML, write_sound_plan(CASE_ID))
    assert isinstance(document, PlanDocument), document
    return document


class TestWritePlan:
    words = st.text(string.ascii_letters + ' ', min_size=1).map(str.strip).filter(bool)
    frontmatters = st.builds(
        Frontmatter,
        id=st.just('20261126-cap-retries'),
        title=words,
        status=st.sampled_from(('draft', 'accepted', 'done')),
        revision=st.integers(min_value=1, max_value=99),
        created=st.dates(),
        head=st.none() | st.text('0123456789abcdef', min_size=7, max_size=7),
        cases=st.dictionaries(st.sampled_from(('C1', 'C2')), words, max_size=2),
        lights=st.sampled_from((None, 'on', 'off')),
        epic=st.none() | words,
        issue=st.none() | words,
    )

    @given(frontmatter=frontmatters)
    def test_the_frontmatter_init_writes_reads_back_unchanged(
        self, frontmatter: Frontmatter
    ) -> None:
        document = read_plan(YAML, write_plan(YAML, frontmatter, load_outline()))

        assert isinstance(document, PlanDocument), document
        assert document.frontmatter == frontmatter

    @given(frontmatter=frontmatters)
    def test_the_skeleton_holds_every_section_in_order(self, frontmatter: Frontmatter) -> None:
        document = read_plan(YAML, write_plan(YAML, frontmatter, load_outline()))

        assert isinstance(document, PlanDocument), document
        assert tuple(section.title for section in document.sections) == load_outline().sections


class TestReadPlan:
    def test_a_criterion_keeps_its_line_number_in_the_file(self) -> None:
        text = write_sound_plan(CASE_ID)

        criteria = read_sound_plan().criteria

        assert [line.number for line in criteria] == [find_line_number(text, CRITERION)]

    def test_a_criterion_yields_the_finding_ids_it_ends_with(self) -> None:
        assert [find_cited_finding_ids(line) for line in read_sound_plan().criteria] == [
            ('C1.e1', 'C1.e2')
        ]

    def test_the_case_aliases_read_back_from_the_frontmatter(self) -> None:
        assert f'{CASE_LINE}{CASE_ID}' in write_sound_plan(CASE_ID)
        assert read_sound_plan().frontmatter.cases == {'C1': CASE_ID}

    @plan_shape_fault_cases()
    def test_a_broken_frontmatter_is_refused_with_its_hint(self, fault: ShapeFault) -> None:
        refused = read_plan(YAML, edit_plan(write_sound_plan(CASE_ID), fault.edits))

        assert isinstance(refused, PlanShapeError)
        assert refused.hint == fault.hint
