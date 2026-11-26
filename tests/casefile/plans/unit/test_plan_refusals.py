"""Each refusal of a plan by name, one fault planted in a valid plan, and the plans let through."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from msgspec.structs import replace
from red_thread_casefile.plans.domain import (
    Accept,
    Acceptance,
    Mitigate,
    Risk,
    YouIntervene,
)
from red_thread_casefile.plans.errors import (
    BlankPlanTextError,
    CrossLaneDependencyError,
    DependencyCycleError,
    DuplicatePlanIdError,
    EmptyRecutError,
    GroundlessAcceptanceError,
    InvalidOwnedPathError,
    InvalidPlanIdError,
    LaneCollisionError,
    MissingAcceptanceError,
    MissingOwnsError,
    NoTicketsError,
    RetiredRestingRefError,
    StrayRecutError,
    UnfitRestingRefError,
    UnknownDependencyError,
    UnknownRestingRefError,
    UnknownRiskTicketError,
    UnlistedCriterionError,
)
from red_thread_casefile.plans.policy import PlanPolicy

from tests.casefile.plans.builders import (
    OPEN_REF,
    RETIRED_REF,
    UNKNOWN_REF,
    add_tickets,
    create_resting_grounds,
    create_ticket_draft,
    create_valid_draft,
    plant_collision,
    plant_cycle,
    plant_groundless,
    replace_ticket,
)
from tests.params import as_params

if TYPE_CHECKING:
    from red_thread_casefile.plans.domain import (
        PlanDraft,
    )


@dataclass(slots=True, kw_only=True, frozen=True)
class Refusal:
    name: str
    draft: PlanDraft
    errors: tuple[type[Exception], ...]
    marks: tuple[pytest.MarkDecorator, ...] = ()


def change_docs(**fields: object) -> PlanDraft:
    draft = create_valid_draft()
    return replace_ticket(draft, 2, replace(draft.tickets[2], **fields))


def rest_docs_on(*refs: str) -> PlanDraft:
    return change_docs(acceptance=(Acceptance(text='the design names each field', rests_on=refs),))


def add_risk(**fields: object) -> PlanDraft:
    risk = Risk(id='R1', risk='the shape drifts', signal='a reader fails', handling=Accept())
    return replace(create_valid_draft(), risks=(replace(risk, **fields),))


def ticket_refusal_cases() -> pytest.MarkDecorator:
    errors = (
        Refusal(
            name='no-tickets',
            draft=replace(create_valid_draft(), tickets=()),
            errors=(NoTicketsError,),
        ),
        Refusal(
            name='no-acceptance', draft=change_docs(acceptance=()), errors=(MissingAcceptanceError,)
        ),
        Refusal(name='no-owns', draft=change_docs(owns=()), errors=(MissingOwnsError,)),
        Refusal(
            name='id-not-a-slug', draft=change_docs(id='Docs_Page'), errors=(InvalidPlanIdError,)
        ),
        Refusal(
            name='lane-not-a-slug', draft=change_docs(lane='the docs'), errors=(InvalidPlanIdError,)
        ),
        Refusal(name='blank-title', draft=change_docs(title=' '), errors=(BlankPlanTextError,)),
        Refusal(
            name='duplicate-id',
            draft=add_tickets(
                create_valid_draft(), create_ticket_draft('docs', 'docs', ('docs/x',))
            ),
            errors=(DuplicatePlanIdError,),
        ),
        Refusal(
            name='owns-absolute',
            draft=change_docs(owns=('/etc/x',)),
            errors=(InvalidOwnedPathError,),
        ),
        Refusal(
            name='owns-climbs',
            draft=change_docs(owns=('docs/../src',)),
            errors=(InvalidOwnedPathError,),
        ),
        Refusal(
            name='owns-class',
            draft=change_docs(owns=('docs/[ab].md',)),
            errors=(InvalidOwnedPathError,),
        ),
        Refusal(name='owns-empty', draft=change_docs(owns=('',)), errors=(InvalidOwnedPathError,)),
    )
    return pytest.mark.parametrize('refusal', as_params(errors))


def grounding_refusal_cases() -> pytest.MarkDecorator:
    errors = (
        Refusal(
            name='groundless',
            draft=plant_groundless(create_valid_draft(), 2),
            errors=(GroundlessAcceptanceError,),
        ),
        Refusal(
            name='unknown-ref', draft=rest_docs_on(UNKNOWN_REF), errors=(UnknownRestingRefError,)
        ),
        Refusal(
            name='retired-ref', draft=rest_docs_on(RETIRED_REF), errors=(RetiredRestingRefError,)
        ),
        Refusal(
            name='open-ref', draft=rest_docs_on('e1', OPEN_REF), errors=(UnfitRestingRefError,)
        ),
        Refusal(
            name='blank-sentence',
            draft=change_docs(acceptance=(Acceptance(text='  ', rests_on=('e1',)),)),
            errors=(BlankPlanTextError,),
        ),
        Refusal(
            name='blank-intent',
            draft=replace(create_valid_draft(), intent=''),
            errors=(BlankPlanTextError,),
        ),
        Refusal(
            name='blank-invariant',
            draft=replace(create_valid_draft(), invariants=('\n',)),
            errors=(BlankPlanTextError,),
        ),
    )
    return pytest.mark.parametrize('refusal', as_params(errors))


def graph_refusal_cases() -> pytest.MarkDecorator:
    errors = (
        Refusal(
            name='unknown-dependency',
            draft=change_docs(depends_on=('ghost',)),
            errors=(UnknownDependencyError,),
        ),
        Refusal(
            name='cross-lane',
            draft=change_docs(depends_on=('plan-record',)),
            errors=(CrossLaneDependencyError,),
        ),
        Refusal(
            name='self-dependency',
            draft=change_docs(depends_on=('docs',)),
            errors=(DependencyCycleError,),
        ),
        Refusal(
            name='cycle', draft=plant_cycle(create_valid_draft()), errors=(DependencyCycleError,)
        ),
        Refusal(
            name='collision',
            draft=plant_collision(create_valid_draft(), 0),
            errors=(LaneCollisionError,),
        ),
        Refusal(
            name='collision-by-glob',
            draft=add_tickets(
                create_valid_draft(), create_ticket_draft('lint', 'tooling', ('**/*.md',))
            ),
            errors=(LaneCollisionError, LaneCollisionError),
        ),
    )
    return pytest.mark.parametrize('refusal', as_params(errors))


def risk_refusal_cases() -> pytest.MarkDecorator:
    errors = (
        Refusal(name='risk-id', draft=add_risk(id='risk-1'), errors=(InvalidPlanIdError,)),
        Refusal(name='blank-signal', draft=add_risk(signal=''), errors=(BlankPlanTextError,)),
        Refusal(
            name='unknown-ticket',
            draft=add_risk(tickets=('ghost',)),
            errors=(UnknownRiskTicketError,),
        ),
        Refusal(
            name='mitigate-unknown-ticket',
            draft=add_risk(handling=Mitigate(ticket='ghost')),
            errors=(UnknownRiskTicketError,),
        ),
        Refusal(
            name='unlisted-criterion',
            draft=add_risk(handling=Mitigate(ticket='docs', criterion='docs exist')),
            errors=(UnlistedCriterionError,),
        ),
        Refusal(
            name='empty-recut', draft=add_risk(handling=YouIntervene()), errors=(EmptyRecutError,)
        ),
        Refusal(
            name='stray-recut',
            draft=add_risk(tickets=('docs',), handling=YouIntervene(recut=('plan-record',))),
            errors=(StrayRecutError,),
        ),
    )
    return pytest.mark.parametrize('refusal', as_params(errors))


def plan_acceptance_cases() -> pytest.MarkDecorator:
    accepted = (
        Refusal(name='valid', draft=create_valid_draft(), errors=()),
        Refusal(
            name='same-lane-overlap',
            draft=add_tickets(
                create_valid_draft(), create_ticket_draft('plan-tests', 'core', ('core/**',))
            ),
            errors=(),
        ),
        Refusal(
            name='listed-criterion',
            draft=add_risk(handling=Mitigate(ticket='docs', criterion='docs holds')),
            errors=(),
        ),
        Refusal(
            name='mitigating-ticket', draft=add_risk(handling=Mitigate(ticket='docs')), errors=()
        ),
        Refusal(
            name='recut-within',
            draft=add_risk(tickets=('docs',), handling=YouIntervene(recut=('docs',))),
            errors=(),
        ),
    )
    return pytest.mark.parametrize('refusal', as_params(accepted))


class TestPlanRefusals:
    grounds = create_resting_grounds()

    def list_named(self, refusal: Refusal) -> tuple[type[Exception], ...]:
        issues = PlanPolicy(draft=refusal.draft, grounds=self.grounds).get_plan_issues()
        return tuple(type(issue) for issue in issues)

    @ticket_refusal_cases()
    def test_a_faulty_ticket_is_refused_by_name(self, refusal: Refusal) -> None:
        assert self.list_named(refusal) == refusal.errors

    @grounding_refusal_cases()
    def test_a_sentence_without_live_grounds_is_refused_by_name(self, refusal: Refusal) -> None:
        assert self.list_named(refusal) == refusal.errors

    @graph_refusal_cases()
    def test_a_faulty_graph_is_refused_by_name(self, refusal: Refusal) -> None:
        assert self.list_named(refusal) == refusal.errors

    @risk_refusal_cases()
    def test_a_faulty_risk_is_refused_by_name(self, refusal: Refusal) -> None:
        assert self.list_named(refusal) == refusal.errors

    @plan_acceptance_cases()
    def test_a_sound_plan_is_let_through(self, refusal: Refusal) -> None:
        assert self.list_named(refusal) == ()
