"""The press over a real case directory and a real git repository."""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.errors import InvalidPageUrlError, LensOverBudgetError, UnknownPlanRefError
from red_thread_casefile.lenses import Plan

from tests.casefile.ledger.builders import QUEUE_LINES, QUEUE_PATH, create_draft, create_valid_draft
from tests.casefile.lenses.reading import find_item, list_headings, list_refs, list_remarks
from tests.casefile.pages.html_reading import (
    list_item_refs,
    list_mermaid,
    list_section_titles,
)
from tests.casefile.pages.promises import (
    assert_page_holds_only_its_own_markup,
    assert_page_shows_flag_kinds,
    assert_page_shows_flags,
)

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet
    from red_thread_casefile.domain import Draft

    from tests.casefile.ledger.git_repository import GitRepository
    from tests.casefile.lenses.builders import DirectoryPressHarness

FINDING = 'the sleep blocks the queue'
DIAGRAM = 'flowchart TD\n  A["queue"] --> B["sleep"]\n  B --> C'
PAGE_URL = 'https://claude.ai/artifact/retry-queue'
EDITED_LINES = (*QUEUE_LINES[:2], '    pass', QUEUE_LINES[3])
SHIFTED_LINES = ('# header', *QUEUE_LINES)


def create_cited_draft(position: int) -> Draft:
    return replace(create_valid_draft('known', position), text=FINDING, cite='src/queue.py:3')


@dataclass(slots=True, kw_only=True, frozen=True)
class DiskChange:
    name: str
    queue_lines: tuple[str, ...] | None = QUEUE_LINES
    advance_head: bool = False
    flags: tuple[str, ...] = ()

    @property
    def param(self) -> ParameterSet:
        return pytest.param(self, id=self.name)

    def apply(self, git: GitRepository) -> tuple[str, ...]:
        recorded = git.head[:7]
        if self.queue_lines is None:
            git.root.joinpath(QUEUE_PATH).unlink()

        if self.queue_lines is not None:
            git.write(QUEUE_PATH, ''.join(f'{line}\n' for line in self.queue_lines))

        if self.advance_head:
            git.write('src/other.py', 'x = 1\n')
            git.commit('move on')

        return tuple(flag.format(recorded=recorded) for flag in self.flags)


def disk_change_cases() -> pytest.MarkDecorator:
    changes = [
        DiskChange(name='untouched'),
        DiskChange(name='line-edited', queue_lines=EDITED_LINES, flags=('citation changed',)),
        DiskChange(name='file-deleted', queue_lines=None, flags=('citation missing',)),
        DiskChange(
            name='line-moved-down',
            queue_lines=SHIFTED_LINES,
            flags=('citation moved to line 4',),
        ),
        DiskChange(name='new-commit', advance_head=True, flags=('lead, recorded at {recorded}',)),
        DiskChange(
            name='new-commit-and-line-edited',
            queue_lines=EDITED_LINES,
            advance_head=True,
            flags=('lead, recorded at {recorded}', 'citation changed'),
        ),
    ]
    return pytest.mark.parametrize('change', [change.param for change in changes])


class TestExportOnDisk:
    @pytest.fixture
    def harness(self, directory_press_harness: DirectoryPressHarness) -> DirectoryPressHarness:
        directory_press_harness.directory.add(
            create_valid_draft('decision', 1),
            create_cited_draft(2),
            create_draft(3, kind='open'),
        )
        return directory_press_harness

    def test_export_writes_out_lens_md_inside_the_case_directory(
        self, harness: DirectoryPressHarness
    ) -> None:
        exported = harness.export('brief')

        written = harness.out_file('out/brief.md')
        assert exported.paths == (written,)
        assert list_headings(written.read_text(encoding='utf-8')) == [
            'Goal',
            'Decided',
            'Constraints',
            'Open',
            'Pointers',
            'How to read',
        ]

    def test_entries_come_through_the_real_ledger_with_text_cite_and_ref(
        self, harness: DirectoryPressHarness
    ) -> None:
        harness.export('brief')

        text = harness.out_file('out/brief.md').read_text(encoding='utf-8')
        assert find_item(text, 'e2') == f'- {FINDING} `src/queue.py:3` [e2]'
        assert list_refs(text, 'Decided') == ['e1']

    def test_exporting_again_replaces_the_file(self, harness: DirectoryPressHarness) -> None:
        harness.export('brief')

        harness.export('brief', Plan(title='A second title', include=()))

        text = harness.out_file('out/brief.md').read_text(encoding='utf-8')
        assert text.splitlines()[0] == '# A second title'
        assert 'Constraints' not in list_headings(text)

    def test_html_is_written_beside_the_markdown(self, harness: DirectoryPressHarness) -> None:
        exported = harness.export('brief', html=True)

        assert exported.paths == (
            harness.out_file('out/brief.md'),
            harness.out_file('out/brief.html'),
        )
        page = harness.out_file('out/brief.html').read_text(encoding='utf-8')
        assert list_item_refs(page) == ['e1', 'e2', 'e3']

    @disk_change_cases()
    def test_flags_follow_the_real_tree_in_markdown_and_html(
        self, harness: DirectoryPressHarness, change: DiskChange
    ) -> None:
        expected = list(change.apply(harness.directory.git))

        harness.export('brief', html=True)

        text = harness.out_file('out/brief.md').read_text(encoding='utf-8')
        page = harness.out_file('out/brief.html').read_text(encoding='utf-8')
        assert list_remarks(find_item(text, 'e2')) == expected
        assert_page_shows_flag_kinds(page, tuple(expected))

    def test_the_board_page_is_written_in_the_case_directory_with_every_live_entry(
        self, harness: DirectoryPressHarness
    ) -> None:
        harness.directory.add(*(create_draft(number, kind='open') for number in range(4, 14)))

        written = harness.press.draw()

        assert written == harness.out_file('board.html')
        page = written.read_text(encoding='utf-8')
        assert list_item_refs(page) == [f'e{number}' for number in range(1, 14)]

    def test_a_diagram_added_through_the_ledger_file_is_drawn_on_the_board_and_a_lens_page(
        self, harness: DirectoryPressHarness
    ) -> None:
        harness.directory.add(replace(create_draft(4, kind='open'), diagram=DIAGRAM))

        harness.press.draw()
        harness.export('brief', html=True)

        board = harness.out_file('board.html').read_text(encoding='utf-8')
        brief = harness.out_file('out/brief.html').read_text(encoding='utf-8')
        assert_page_holds_only_its_own_markup(board)
        assert list_mermaid(board)[0] == DIAGRAM
        assert list_section_titles(board)[-1] == 'Map'
        assert list_mermaid(brief) == [DIAGRAM]

    def test_the_board_page_carries_the_flags_of_the_real_tree(
        self, harness: DirectoryPressHarness
    ) -> None:
        change = DiskChange(name='edit', queue_lines=EDITED_LINES, flags=('citation changed',))
        change.apply(harness.directory.git)

        harness.press.draw()

        page = harness.out_file('board.html').read_text(encoding='utf-8')
        assert_page_shows_flags(page, change.flags)


class TestRefusalsOnDisk:
    @pytest.fixture
    def harness(self, directory_press_harness: DirectoryPressHarness) -> DirectoryPressHarness:
        directory_press_harness.directory.add(create_cited_draft(1), create_draft(2, kind='open'))
        return directory_press_harness

    def test_an_unknown_ref_writes_nothing(self, harness: DirectoryPressHarness) -> None:
        with pytest.raises(UnknownPlanRefError):
            harness.export('brief', Plan(include=('e9',)), html=True)

        assert not harness.out_file('out').exists()

    def test_an_over_budget_output_leaves_the_earlier_file_byte_for_byte(
        self, harness: DirectoryPressHarness
    ) -> None:
        harness.export('brief')
        earlier = harness.out_file('out/brief.md').read_bytes()
        harness.directory.add(*(create_draft(number, kind='open') for number in range(3, 73)))

        with pytest.raises(LensOverBudgetError) as raised:
            harness.export('brief', html=True)

        assert (raised.value.lens, raised.value.budget) == ('brief', 60)
        assert raised.value.lines > 60
        assert harness.out_file('out/brief.md').read_bytes() == earlier
        assert not harness.out_file('out/brief.html').exists()

    def test_an_over_budget_first_export_creates_no_output_folder(
        self, harness: DirectoryPressHarness
    ) -> None:
        harness.directory.add(*(create_draft(number, kind='open') for number in range(3, 73)))

        with pytest.raises(LensOverBudgetError):
            harness.export('brief')

        assert not harness.out_file('out').exists()


class TestRecordPageOnDisk:
    @pytest.fixture
    def harness(self, directory_press_harness: DirectoryPressHarness) -> DirectoryPressHarness:
        directory_press_harness.directory.add(create_draft(1, kind='open'))
        return directory_press_harness

    def test_the_link_is_stored_in_case_json_and_nothing_else_in_it_changes(
        self, harness: DirectoryPressHarness
    ) -> None:
        before = harness.read_case_record()

        returned = harness.press.record_page(PAGE_URL)

        assert returned.page_url == PAGE_URL
        assert harness.read_case_record() == {**before, 'page_url': PAGE_URL}

    def test_the_ledger_file_is_not_touched(self, harness: DirectoryPressHarness) -> None:
        before = harness.directory.ledger_file.read_bytes()

        harness.press.record_page(PAGE_URL)

        assert harness.directory.ledger_file.read_bytes() == before

    @pytest.mark.parametrize(
        'url',
        [
            pytest.param('http://example.invalid/b', id='http'),
            pytest.param('https://example.invalid/a b', id='whitespace'),
        ],
    )
    def test_a_rejected_link_leaves_case_json_byte_for_byte(
        self, harness: DirectoryPressHarness, url: str
    ) -> None:
        before = harness.out_file('case.json').read_bytes()

        with pytest.raises(InvalidPageUrlError):
            harness.press.record_page(url)

        assert harness.out_file('case.json').read_bytes() == before

    def test_the_recorded_link_is_what_a_fresh_board_shows(
        self, harness: DirectoryPressHarness
    ) -> None:
        harness.press.record_page(PAGE_URL)

        shown = harness.directory.casefile.show()

        assert f'Page: {PAGE_URL}' in shown.splitlines()

    def test_the_recorded_link_is_what_a_fresh_export_points_to(
        self, harness: DirectoryPressHarness
    ) -> None:
        harness.press.record_page(PAGE_URL)

        harness.export('brief')

        text = harness.out_file('out/brief.md').read_text(encoding='utf-8')
        assert f'- Board: {PAGE_URL}' in text.splitlines()
