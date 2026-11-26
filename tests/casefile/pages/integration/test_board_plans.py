"""The board on disk lists the plans in .red-thread/plans/ that cite its case."""

import json
from typing import TYPE_CHECKING

from tests.casefile.pages.html_reading import list_facts

if TYPE_CHECKING:
    from tests.casefile.lenses.builders import DirectoryPressHarness


class TestBoardPlansOnDisk:
    def put_plan(self, harness: DirectoryPressHarness, plan_id: str, cases: list[str]) -> None:
        home = harness.case_directory.parent.joinpath('plans', plan_id)
        home.mkdir(parents=True)
        index = {'id': plan_id, 'title': f'Plan {plan_id}', 'at': 'now', 'cases': cases}
        home.joinpath('plan.json').write_text(json.dumps(index), encoding='utf-8')

    def test_a_plan_beside_the_case_that_cites_it_is_linked_from_the_board(
        self, directory_press_harness: DirectoryPressHarness
    ) -> None:
        case_id = directory_press_harness.case_directory.name
        self.put_plan(directory_press_harness, 'cut', [case_id])
        self.put_plan(directory_press_harness, 'other', ['another-case'])

        page = directory_press_harness.press.draw().read_text(encoding='utf-8')

        plans = list_facts(page)[-1]
        assert (plans.label, plans.value, plans.link) == (
            'Plans',
            'Plan cut',
            '../plans/cut/plan.html',
        )
