"""What the yaml block of a finding may hold, and how check names a block it cannot read."""

from types import MappingProxyType
from typing import TYPE_CHECKING

import msgspec
import pytest
from red_thread_casefile.errors import MalformedBlockError, StrayTextError

from tests.casefile.findings.blocks import encode_block, read_case_text, write_blocks_case
from tests.casefile.findings.cases import shape_problem_params, unreadable_block_params

if TYPE_CHECKING:
    from red_thread_casefile.schemas import CaseReading

    from tests.casefile.findings.cases import ShapeCase


def shape_problem_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('case', shape_problem_params())


def unreadable_block_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('block', unreadable_block_params())


class TestBlockFields:
    every_field = MappingProxyType({
        'kind': 'known',
        'text': 'the sleep blocks',
        'source': 'scout',
        'verdict': 'VERIFIED',
        'cite': 'src/queue.py:3',
        'quote': 'time.sleep(job.delay)',
        'addr': 'src/queue.py#retry',
        'rests_on': 'a 4.x docs page',
        'refute': 'an observation',
        'diagram': 'flowchart TD\n  A --> B',
        'supersedes': ('e1', 'T1.e2'),
    })

    def read_blocks(self, *blocks: str) -> CaseReading:
        return read_case_text(write_blocks_case(blocks))

    @shape_problem_cases()
    def test_a_field_the_block_may_not_hold_is_named_at_its_finding(self, case: ShapeCase) -> None:
        reading = self.read_blocks(encode_block(case.record))

        problems = [p for p in reading.problems if isinstance(p, MalformedBlockError)]

        assert len(reading.problems) == 1
        assert [problem.location.finding_id for problem in problems] == ['e1']
        assert case.field_name in problems[0].reason
        assert reading.located == ()

    @unreadable_block_cases()
    def test_a_block_that_is_no_mapping_of_fields_is_named_at_its_finding(self, block: str) -> None:
        reading = self.read_blocks(block)

        problems = [p for p in reading.problems if isinstance(p, MalformedBlockError)]

        assert len(reading.problems) == 1
        assert [problem.location.finding_id for problem in problems] == ['e1']

    def test_every_field_reaches_the_finding(self) -> None:
        reading = self.read_blocks(encode_block(dict(self.every_field)))

        [finding] = reading.ledger.findings

        written = msgspec.to_builtins(finding)
        assert {name: written[name] for name in self.every_field} == dict(self.every_field)
        assert reading.problems == ()

    def test_a_plain_scalar_is_trimmed_by_yaml_and_a_quoted_one_is_kept(self) -> None:
        reading = self.read_blocks("kind: open\ntext:   padded   \nsource: ' scout '\n")

        [finding] = reading.ledger.findings

        assert (finding.text, finding.source) == ('padded', ' scout ')

    def test_a_good_block_after_a_bad_one_is_still_read(self) -> None:
        good = encode_block({'kind': 'open', 'text': 'a', 'source': 'scout'})

        reading = self.read_blocks(encode_block({'kind': 'guess'}), good)

        problems = [p for p in reading.problems if isinstance(p, MalformedBlockError)]

        assert [finding.finding_id for finding in reading.ledger.findings] == ['e2']
        assert len(reading.problems) == 1
        assert [problem.location.finding_id for problem in problems] == ['e1']

    def test_text_after_a_closed_block_is_a_fault_and_the_finding_is_still_read(self) -> None:
        good = encode_block({'kind': 'open', 'text': 'a', 'source': 'scout'})

        reading = read_case_text(f'{write_blocks_case([good])}after the block\n')

        assert [finding.finding_id for finding in reading.ledger.findings] == ['e1']
        assert [type(problem) for problem in reading.problems] == [StrayTextError]
