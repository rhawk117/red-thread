"""The cases a plan names: at least one, each under an alias C1, C2 and so on, each a real case."""

from msgspec.structs import replace
from red_thread_plans.errors import InvalidPlanIdError, NoCasesError, UnknownCaseError
from red_thread_plans.policy import PlanPolicy

from tests.casefile.ledger.builders import CASE_ID
from tests.plans.revisions.builders import create_resting_grounds, create_valid_draft


class TestCaseAliases:
    grounds = create_resting_grounds()

    def list_case_issues(self, cases: dict[str, str]) -> list[type[Exception]]:
        draft = replace(create_valid_draft(), cases=cases)
        found = PlanPolicy(draft=draft, grounds=self.grounds).get_case_issues()
        return [type(problem) for problem in found]

    def test_a_plan_on_one_known_case_has_no_case_issue(self) -> None:
        assert self.list_case_issues({'C1': CASE_ID}) == []

    def test_a_plan_that_names_no_case_is_refused(self) -> None:
        assert self.list_case_issues({}) == [NoCasesError]

    def test_an_alias_that_is_not_c_and_a_number_is_refused(self) -> None:
        assert self.list_case_issues({'case1': CASE_ID}) == [InvalidPlanIdError]

    def test_an_alias_whose_case_was_not_found_is_refused(self) -> None:
        assert self.list_case_issues({'C1': CASE_ID, 'C2': 'gone'}) == [UnknownCaseError]
