"""CaseFile.check over any written entries: what is written reads back, and every fault is named."""

from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st
from msgspec.structs import replace
from red_thread_casefile.domain import THREAD_NAME
from red_thread_casefile.errors import SecretInEntryError, StrayThreadFileError, UncitedKnownError

from tests.casefile.entries.strategies import POOLED_THREADS, words
from tests.casefile.ledger.builders import create_entry
from tests.casefile.ledger.markdown import write_thread_text
from tests.casefile.redaction.strategies import planted_secrets
from tests.casefile.services.fakes import create_service_harness

if TYPE_CHECKING:
    from red_thread_casefile.domain import Entry

    from tests.casefile.redaction.strategies import Planted
    from tests.casefile.services.fakes import ServiceHarness

type Batch = tuple[str | None, list[str]]


def is_not_thread_name(name: str) -> bool:
    return not THREAD_NAME.fullmatch(name)


def write_next(harness: ServiceHarness, entry: Entry) -> Entry:
    seq = len(harness.scribe.files[entry.thread]) + 1
    numbered = replace(entry, seq=seq, round=seq)
    harness.seed(numbered)
    return numbered


def write_batches(harness: ServiceHarness, batches: list[Batch]) -> list[Entry]:
    return [
        write_next(harness, create_entry(thread=thread, text=text))
        for thread, texts in batches
        for text in texts
    ]


def join_planted(group: list[Planted], *, redacted: bool) -> str:
    return ' '.join(planted.redacted if redacted else planted.whole for planted in group)


def plant_entry(group: list[Planted]) -> Entry:
    whole = join_planted(group, redacted=False)
    return create_entry(
        text=f'note {whole}',
        rests_on=f'on {whole}',
        diagram=f'flowchart TD\n  A {whole}',
    )


def expect_secrets(ref: str, group: list[Planted]) -> list[tuple[str, str, str]]:
    if not group:
        return []

    redacted = join_planted(group, redacted=True)
    return [
        (ref, 'text', f'note {redacted}'),
        (ref, 'rests_on', f'on {redacted}'),
        (ref, 'diagram', f'flowchart TD\n  A {redacted}'),
    ]


class TestEntryCheckProperties:
    batches = st.tuples(
        st.sampled_from(POOLED_THREADS),
        st.lists(words, min_size=1, max_size=4),
    )
    batch_runs = st.lists(batches, min_size=1, max_size=6)
    stray_names = st.from_regex(r'[A-Za-z0-9_-]{1,8}', fullmatch=True).filter(is_not_thread_name)
    secret_groups = st.lists(st.lists(planted_secrets, max_size=3), min_size=1, max_size=3)

    @given(run=batch_runs)
    def test_written_entries_read_back_as_written_with_no_fault(self, run: list[Batch]) -> None:
        harness = create_service_harness()

        written = write_batches(harness, run)

        assert sorted(harness.read_entries(), key=str) == sorted(written, key=str)
        assert harness.case_file.check().problems == ()

    @given(run=batch_runs, data=st.data())
    def test_one_faulty_entry_among_good_ones_is_the_one_fault_named(
        self, run: list[Batch], data: st.DataObject
    ) -> None:
        harness = create_service_harness()
        write_batches(harness, run)
        thread = data.draw(st.sampled_from(POOLED_THREADS))
        bad = write_next(harness, create_entry(kind='known', thread=thread, text='unproven'))
        write_batches(harness, data.draw(st.lists(self.batches, max_size=2)))
        before = dict(harness.store.files)

        problems = harness.case_file.check().problems

        uncited = [p.spot.ref for p in problems if isinstance(p, UncitedKnownError)]
        assert uncited == [bad.ref]
        assert len(problems) == 1
        assert harness.store.files == before

    @given(run=batch_runs, name=stray_names)
    def test_a_file_in_threads_that_is_no_thread_is_named(
        self, run: list[Batch], name: str
    ) -> None:
        harness = create_service_harness()
        write_batches(harness, run)
        stray = f'threads/{name}.md'
        harness.store.write(stray, write_thread_text([create_entry()]))

        problems = harness.case_file.check().problems

        assert [p.file for p in problems if isinstance(p, StrayThreadFileError)] == [stray]
        assert len(problems) == 1

    @given(groups=secret_groups)
    def test_every_planted_secret_is_named_by_its_entry_and_field_and_never_echoed(
        self, groups: list[list[Planted]]
    ) -> None:
        harness = create_service_harness()
        written = [write_next(harness, plant_entry(group)) for group in groups]

        problems = harness.case_file.check().problems

        secrets = [p for p in problems if isinstance(p, SecretInEntryError)]
        found = [(secret.spot.ref, secret.field, secret.scrubbed) for secret in secrets]
        expected = [
            item
            for entry, group in zip(written, groups, strict=True)
            for item in expect_secrets(entry.ref, group)
        ]
        assert found == expected
        assert len(problems) == len(secrets)
