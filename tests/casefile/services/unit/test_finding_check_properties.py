"""CaseFile.check over any findings: what is written reads back, and every fault is named."""

from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.domain import THREAD_NAME
from red_thread_casefile.errors import SecretInFindingError, StrayThreadFileError, UncitedKnownError

from tests.casefile.findings.strategies import POOLED_THREADS, words
from tests.casefile.ledger.builders import create_finding
from tests.casefile.ledger.markdown import write_thread_text
from tests.casefile.redaction.strategies import planted_secrets
from tests.casefile.services.fakes import create_service_harness

if TYPE_CHECKING:
    from red_thread_casefile.domain import CaseFinding

    from tests.casefile.redaction.strategies import Planted
    from tests.casefile.services.fakes import ServiceHarness

type Batch = tuple[str | None, list[str]]


def is_not_thread_name(name: str) -> bool:
    return not THREAD_NAME.fullmatch(name)


def write_next(harness: ServiceHarness, finding: CaseFinding) -> CaseFinding:
    finding_number = len(harness.scribe.files[finding.thread]) + 1
    numbered = finding.replace_with(finding_number=finding_number, round=finding_number)
    harness.seed(numbered)
    return numbered


def write_batches(harness: ServiceHarness, batches: list[Batch]) -> list[CaseFinding]:
    return [
        write_next(harness, create_finding(thread=thread, text=text))
        for thread, texts in batches
        for text in texts
    ]


def join_planted(group: list[Planted], *, redacted: bool) -> str:
    return ' '.join(planted.redacted if redacted else planted.whole for planted in group)


def plant_finding(group: list[Planted]) -> CaseFinding:
    whole = join_planted(group, redacted=False)
    return create_finding(
        text=f'note {whole}',
        rests_on=f'on {whole}',
        diagram=f'flowchart TD\n  A {whole}',
    )


def expect_secrets(finding_id: str, group: list[Planted]) -> list[tuple[str, str, str]]:
    if not group:
        return []

    redacted = join_planted(group, redacted=True)
    return [
        (finding_id, 'text', f'note {redacted}'),
        (finding_id, 'rests_on', f'on {redacted}'),
        (finding_id, 'diagram', f'flowchart TD\n  A {redacted}'),
    ]


class TestFindingCheckProperties:
    batches = st.tuples(
        st.sampled_from(POOLED_THREADS),
        st.lists(words, min_size=1, max_size=4),
    )
    batch_runs = st.lists(batches, min_size=1, max_size=6)
    stray_names = st.from_regex(r'[A-Za-z0-9_-]{1,8}', fullmatch=True).filter(is_not_thread_name)
    secret_groups = st.lists(st.lists(planted_secrets, max_size=3), min_size=1, max_size=3)

    @given(run=batch_runs)
    def test_written_findings_read_back_as_written_with_no_fault(self, run: list[Batch]) -> None:
        harness = create_service_harness()

        written = write_batches(harness, run)

        assert sorted(harness.read_findings(), key=str) == sorted(written, key=str)
        assert harness.case_file.check().problems == ()

    @given(run=batch_runs, data=st.data())
    def test_one_faulty_finding_among_good_ones_is_the_one_fault_named(
        self, run: list[Batch], data: st.DataObject
    ) -> None:
        harness = create_service_harness()
        write_batches(harness, run)
        thread = data.draw(st.sampled_from(POOLED_THREADS))
        bad = write_next(harness, create_finding(kind='known', thread=thread, text='unproven'))
        write_batches(harness, data.draw(st.lists(self.batches, max_size=2)))
        before = dict(harness.store.files)

        problems = harness.case_file.check().problems

        uncited = [p.location.finding_id for p in problems if isinstance(p, UncitedKnownError)]
        assert uncited == [bad.finding_id]
        assert len(problems) == 1
        assert harness.store.files == before

    @given(run=batch_runs, name=stray_names)
    def test_a_file_in_threads_that_is_no_thread_is_named(
        self, run: list[Batch], name: str
    ) -> None:
        harness = create_service_harness()
        write_batches(harness, run)
        stray = f'threads/{name}.md'
        harness.store.write(stray, write_thread_text([create_finding()]))

        problems = harness.case_file.check().problems

        assert [p.file for p in problems if isinstance(p, StrayThreadFileError)] == [stray]
        assert len(problems) == 1

    @given(groups=secret_groups)
    def test_every_planted_secret_is_named_by_its_finding_and_field_and_never_echoed(
        self, groups: list[list[Planted]]
    ) -> None:
        harness = create_service_harness()
        written = [write_next(harness, plant_finding(group)) for group in groups]

        problems = harness.case_file.check().problems

        secrets = [p for p in problems if isinstance(p, SecretInFindingError)]
        found = [(secret.location.finding_id, secret.field, secret.scrubbed) for secret in secrets]
        expected = [
            item
            for finding, group in zip(written, groups, strict=True)
            for item in expect_secrets(finding.finding_id, group)
        ]
        assert found == expected
        assert len(problems) == len(secrets)
