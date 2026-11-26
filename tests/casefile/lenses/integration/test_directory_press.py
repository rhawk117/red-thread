"""The press over a real case directory and a real git repository."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from red_thread_casefile.errors import (
    LensOverBudgetError,
    UnknownSelectionRefError,
)
from red_thread_casefile.lenses import Selection

from tests.casefile.ledger.builders import QUEUE_LINES, QUEUE_PATH, create_valid_entry
from tests.casefile.lenses.builders import export
from tests.casefile.lenses.cases import QUEUE_CITE, QUEUE_QUOTE
from tests.casefile.lenses.reading import (
    find_item,
    list_headings,
    list_refs,
    list_remarks,
    list_section_lines,
)
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
from tests.params import as_params

if TYPE_CHECKING:
    from red_thread_casefile.domain import Entry

    from tests.casefile.ledger.git_repository import GitRepository
    from tests.casefile.lenses.builders import DirectoryPressHarness

FINDING = 'the sleep blocks the queue'
DIAGRAM = 'flowchart TD\n  A["queue"] --> B["sleep"]\n  B --> C'
PAGE_URL = 'https://claude.ai/artifact/retry-queue'
EDITED_LINES = (*QUEUE_LINES[:2], '    pass', QUEUE_LINES[3])
SHIFTED_LINES = ('# header', *QUEUE_LINES)


def create_cited_entry(position: int) -> Entry:
    known = create_valid_entry('known', position)
    return known.replace_with(text=FINDING, cite=QUEUE_CITE, quote=QUEUE_QUOTE)


@dataclass(slots=True, kw_only=True, frozen=True)
class DiskChange:
    name: str
    queue_lines: tuple[str, ...] | None = QUEUE_LINES
    advance_head: bool = False
    flags: tuple[str, ...] = ()
    marks: tuple[pytest.MarkDecorator, ...] = ()

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
    return pytest.mark.parametrize('change', as_params(changes))


class TestExportOnDisk:
    @pytest.fixture
    def harness(self, directory_press_harness: DirectoryPressHarness) -> DirectoryPressHarness:
        directory_press_harness.seed(
            create_valid_entry('decision', 1),
            create_cited_entry(2),
            create_valid_entry('open', 3),
        )
        return directory_press_harness

    def test_export_writes_out_lens_md_inside_the_case_directory(
        self, harness: DirectoryPressHarness
    ) -> None:
        exported = export(harness, 'brief')

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

    def test_the_pointers_name_the_case_file_that_holds_the_entries(
        self, harness: DirectoryPressHarness
    ) -> None:
        export(harness, 'brief')

        text = harness.out_file('out/brief.md').read_text(encoding='utf-8')
        (line,) = [line for line in list_section_lines(text, 'Pointers') if 'Case file' in line]
        named = line.split('`')[1]
        assert harness.directory.git.root.joinpath(named).resolve() == harness.directory.case_file

    def test_entries_come_through_the_real_ledger_with_text_cite_and_ref(
        self, harness: DirectoryPressHarness
    ) -> None:
        export(harness, 'brief')

        text = harness.out_file('out/brief.md').read_text(encoding='utf-8')
        assert find_item(text, 'e2') == f'- {FINDING} `src/queue.py:3` [e2]'
        assert list_refs(text, 'Decided') == ['e1']

    def test_exporting_again_replaces_the_file(self, harness: DirectoryPressHarness) -> None:
        export(harness, 'brief')

        export(harness, 'brief', Selection(title='A second title', include=()))

        text = harness.out_file('out/brief.md').read_text(encoding='utf-8')
        assert text.splitlines()[0] == '# A second title'
        assert 'Constraints' not in list_headings(text)

    def test_html_is_written_beside_the_markdown(self, harness: DirectoryPressHarness) -> None:
        exported = export(harness, 'brief', html=True)

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

        export(harness, 'brief', html=True)

        text = harness.out_file('out/brief.md').read_text(encoding='utf-8')
        page = harness.out_file('out/brief.html').read_text(encoding='utf-8')
        assert list_remarks(find_item(text, 'e2')) == expected
        assert_page_shows_flag_kinds(page, tuple(expected))

    def test_the_board_page_is_written_in_the_case_directory_with_every_live_entry(
        self, harness: DirectoryPressHarness
    ) -> None:
        harness.seed(*(create_valid_entry('open', number) for number in range(4, 14)))

        written = harness.press.draw()

        assert written == harness.out_file('board.html')
        page = written.read_text(encoding='utf-8')
        assert list_item_refs(page) == [f'e{number}' for number in range(1, 14)]

    def test_a_diagram_added_through_the_ledger_file_is_drawn_on_the_board_and_a_lens_page(
        self, harness: DirectoryPressHarness
    ) -> None:
        harness.seed(create_valid_entry('open', 4).replace_with(diagram=DIAGRAM))

        harness.press.draw()
        export(harness, 'brief', html=True)

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
        directory_press_harness.seed(create_cited_entry(1), create_valid_entry('open', 2))
        return directory_press_harness

    def test_an_unknown_ref_writes_nothing(self, harness: DirectoryPressHarness) -> None:
        with pytest.raises(UnknownSelectionRefError):
            export(harness, 'brief', Selection(include=('e9',)), html=True)

        assert not harness.out_file('out').exists()

    def test_an_over_budget_output_leaves_the_earlier_file_byte_for_byte(
        self, harness: DirectoryPressHarness
    ) -> None:
        export(harness, 'brief')
        earlier = harness.out_file('out/brief.md').read_bytes()
        harness.seed(*(create_valid_entry('open', number) for number in range(3, 73)))

        with pytest.raises(LensOverBudgetError) as raised:
            export(harness, 'brief', html=True)

        assert (raised.value.lens, raised.value.budget) == ('brief', 60)
        assert raised.value.lines > 60
        assert harness.out_file('out/brief.md').read_bytes() == earlier
        assert not harness.out_file('out/brief.html').exists()

    def test_an_over_budget_first_export_creates_no_output_folder(
        self, harness: DirectoryPressHarness
    ) -> None:
        harness.seed(*(create_valid_entry('open', number) for number in range(3, 73)))

        with pytest.raises(LensOverBudgetError):
            export(harness, 'brief')

        assert not harness.out_file('out').exists()


class TestPageUrlOnDisk:
    @pytest.fixture
    def harness(self, directory_press_harness: DirectoryPressHarness) -> DirectoryPressHarness:
        directory_press_harness.seed(create_valid_entry('open', 1))
        directory_press_harness.write_page_url(PAGE_URL)
        return directory_press_harness

    def test_a_link_written_into_case_md_is_what_a_fresh_board_shows(
        self, harness: DirectoryPressHarness
    ) -> None:
        shown = harness.directory.casefile.show()

        assert f'Page: {PAGE_URL}' in shown.splitlines()

    def test_a_link_written_into_case_md_is_what_a_fresh_export_points_to(
        self, harness: DirectoryPressHarness
    ) -> None:
        export(harness, 'brief')

        text = harness.out_file('out/brief.md').read_text(encoding='utf-8')
        assert f'- Board: {PAGE_URL}' in text.splitlines()
