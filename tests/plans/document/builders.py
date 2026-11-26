"""Plan text the plan tests share: the skeleton init writes, filled in section by section."""

from datetime import date
from typing import TYPE_CHECKING

from red_thread_plans.domain import HEADING, Frontmatter
from red_thread_plans.schemas import write_plan

if TYPE_CHECKING:
    from collections.abc import Mapping

PLAN_ID = '20261126-cap-retries'
TITLE = 'Cap the attempts of each job'
CREATED = date(2026, 11, 26)
CASE_LINE = '  C1: '
CRITERION = '- A job that fails five times is not run a sixth time. (C1.e1, C1.e2)'
SOUND_SECTIONS = {
    'Intent': 'Stop a failing job from running without end.',
    'Approach': 'Count the attempts beside the job, where C1.e1 says the queue keeps it.',
    'Acceptance': CRITERION,
    'Tasks': '1. Count each attempt.\n2. Stop the job at the cap.',
}


def create_frontmatter(*case_ids: str) -> Frontmatter:
    cases = {f'C{number}': case_id for number, case_id in enumerate(case_ids, 1)}
    return Frontmatter(id=PLAN_ID, title=TITLE, created=CREATED, cases=cases)


def fill_section(text: str, title: str, body: str) -> str:
    heading = f'{HEADING}{title}\n'
    return text.replace(heading, f'{heading}\n{body}\n', 1)


def fill_plan(text: str, sections: Mapping[str, str]) -> str:
    filled = text
    for title, body in sections.items():
        filled = fill_section(filled, title, body)
    return filled


def write_sound_plan(*case_ids: str) -> str:
    return fill_plan(write_plan(create_frontmatter(*case_ids)), SOUND_SECTIONS)


def edit_plan(text: str, edits: tuple[tuple[str, str], ...]) -> str:
    edited = text
    for old, new in edits:
        edited = edited.replace(old, new, 1)
    return edited


def find_line_number(text: str, line: str) -> int:
    return text.splitlines().index(line) + 1
