"""PlanPolicy: a sound plan has its sections written and its criteria on live findings."""

from dataclasses import dataclass
from types import NoneType

import pytest
from red_thread_casefile.domain import CaseLedger
from red_thread_plans.domain import PlanDocument
from red_thread_plans.errors import (
    EmptySectionError,
    GroundlessCriterionError,
    MissingSectionError,
    NoCasesError,
    NoCriteriaError,
    RetiredFindingError,
    UnknownCaseError,
    UnknownFindingError,
    UnsetLightsError,
    WrongFindingKindError,
)
from red_thread_plans.packaged import load_outline
from red_thread_plans.policy import PlanPolicy, create_grounds
from red_thread_plans.schemas import read_plan

from tests.casefile.ledger.builders import create_finding
from tests.codec import YAML
from tests.params import as_params
from tests.plans.document.builders import (
    CRITERION,
    SOUND_SECTIONS,
    edit_plan,
    find_line_number,
    write_sound_plan,
)

CASE_ID = '20261121-retry-queue-slowdown'
FINDING_IDS = '(C1.e1, C1.e2)'


@dataclass(slots=True, kw_only=True, frozen=True)
class PlanFault:
    name: str
    edits: tuple[tuple[str, str], ...]
    issue_types: tuple[type[object], ...]
    marks: tuple[pytest.MarkDecorator, ...] = ()


def create_fault(name: str, *edits: tuple[str, str], issue: type[object] = NoneType) -> PlanFault:
    found = () if issue is NoneType else (issue,)
    return PlanFault(name=name, edits=edits, issue_types=found)


def plan_policy_fault_cases() -> pytest.MarkDecorator:
    intent = SOUND_SECTIONS['Intent']
    faults = (
        create_fault('sound'),
        create_fault('groundless', (FINDING_IDS, ''), issue=GroundlessCriterionError),
        create_fault('unknown-finding-id', (FINDING_IDS, '(C1.e9)'), issue=UnknownFindingError),
        create_fault('retired-finding-id', (FINDING_IDS, '(C1.e4)'), issue=RetiredFindingError),
        create_fault('open-finding-id', (FINDING_IDS, '(C1.e3)'), issue=WrongFindingKindError),
        create_fault(
            'unknown-finding-id-in-approach',
            ('C1.e1 says', 'C1.e9 says'),
            issue=UnknownFindingError,
        ),
        create_fault('open-finding-id-in-approach', ('C1.e1 says', 'C1.e3 says')),
        create_fault('missing-section', ('## Risks\n', ''), issue=MissingSectionError),
        create_fault('empty-intent', (intent, ''), issue=EmptySectionError),
        create_fault(
            'no-criterion', (CRITERION, CRITERION.removeprefix('- ')), issue=NoCriteriaError
        ),
        create_fault(
            'accepted-in-the-dark', ('status: draft', 'status: accepted'), issue=UnsetLightsError
        ),
        create_fault(
            'accepted-lights-on',
            ('status: draft', 'status: accepted'),
            ('lights: null', "lights: 'on'"),
        ),
    )
    return pytest.mark.parametrize('fault', as_params(faults))


def create_ledger() -> CaseLedger:
    return CaseLedger(
        findings=(
            create_finding(finding_number=1, kind='known'),
            create_finding(finding_number=2, kind='decision', source='user'),
            create_finding(finding_number=3, kind='open'),
            create_finding(finding_number=4, kind='known'),
            create_finding(finding_number=5, kind='known', supersedes=('e4',)),
        )
    )


def read_document(text: str) -> PlanDocument:
    document = read_plan(YAML, text)
    assert isinstance(document, PlanDocument), document
    return document


class TestPlanPolicy:
    grounds = create_grounds({'C1': create_ledger()})

    def find_issue_types(self, text: str) -> tuple[type[object], ...]:
        policy = PlanPolicy(
            document=read_document(text), grounds=self.grounds, outline=load_outline()
        )
        return tuple(map(type, policy.get_plan_issues()))

    @plan_policy_fault_cases()
    def test_each_fault_is_named_and_a_sound_plan_has_none(self, fault: PlanFault) -> None:
        text = edit_plan(write_sound_plan(CASE_ID), fault.edits)

        assert self.find_issue_types(text) == fault.issue_types

    def test_an_unfit_finding_id_names_the_line_of_its_criterion(self) -> None:
        text = edit_plan(write_sound_plan(CASE_ID), ((FINDING_IDS, '(C1.e3)'),))
        policy = PlanPolicy(
            document=read_document(text), grounds=self.grounds, outline=load_outline()
        )

        issues = policy.get_plan_issues()

        assert [issue.line for issue in issues if isinstance(issue, WrongFindingKindError)] == [
            find_line_number(text, CRITERION.replace(FINDING_IDS, '(C1.e3)'))
        ]

    def test_a_plan_with_no_case_is_refused_for_that_alone(self) -> None:
        assert self.find_issue_types(write_sound_plan()) == (NoCasesError,)

    def test_a_missing_case_is_named_and_its_finding_ids_are_not_checked(self) -> None:
        document = read_document(write_sound_plan(CASE_ID))
        policy = PlanPolicy(
            document=document,
            grounds=create_grounds({}),
            missing={'C1': CASE_ID},
            outline=load_outline(),
        )

        issues = policy.get_plan_issues()

        assert tuple(map(type, issues)) == (UnknownCaseError,)
