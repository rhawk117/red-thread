"""Scenarios for the batch rules: what a draft needs to be stored."""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from red_thread_casefile.errors import (
    DecisionInThreadError,
    DecisionSourceError,
    MissingRefuteError,
    MissingRestsOnError,
    OwnerInThreadError,
    UncitedKnownError,
    UncitedRuledOutError,
    UpgradedVerdictError,
)

from tests.casefile.ledger.builders import URL_CITE, create_draft, create_valid_draft
from tests.params import as_labelled_params, as_params

if TYPE_CHECKING:
    import pytest
    from _pytest.mark import ParameterSet
    from red_thread_casefile.domain import Draft
    from red_thread_casefile.errors import CaseFileError


@dataclass(slots=True, kw_only=True, frozen=True)
class RuleCase:
    name: str
    draft: Draft
    error_type: type[CaseFileError] | None
    thread: str | None = None
    marks: tuple[pytest.MarkDecorator, ...] = ()


def status_rule_params() -> list[ParameterSet]:
    known = create_valid_draft('known')
    cases = [
        RuleCase(
            name='known-without-cite',
            draft=replace(known, cite=None),
            error_type=UncitedKnownError,
        ),
        RuleCase(
            name='known-without-cite-or-verdict',
            draft=replace(known, cite=None, verdict=None),
            error_type=UncitedKnownError,
        ),
        RuleCase(
            name='known-inferred',
            draft=replace(known, verdict='INFERRED', rests_on='a 4.x docs page'),
            error_type=UpgradedVerdictError,
        ),
        RuleCase(
            name='known-needs-analysis',
            draft=replace(known, verdict='NEEDS-ANALYSIS'),
            error_type=UpgradedVerdictError,
        ),
        RuleCase(
            name='known-blocked',
            draft=replace(known, verdict='BLOCKED'),
            error_type=UpgradedVerdictError,
        ),
        RuleCase(
            name='inferred-open-without-rests-on',
            draft=replace(create_draft(kind='open'), verdict='INFERRED'),
            error_type=MissingRestsOnError,
        ),
        RuleCase(
            name='inferred-hypothesis-without-rests-on',
            draft=replace(
                create_valid_draft('hypothesis'),
                verdict='INFERRED',
            ),
            error_type=MissingRestsOnError,
        ),
        RuleCase(
            name='known-verified',
            draft=known,
            error_type=None,
        ),
        RuleCase(
            name='known-with-no-verdict',
            draft=replace(known, verdict=None),
            error_type=None,
        ),
        RuleCase(
            name='known-with-command-cite',
            draft=replace(known, cite='grep -rn sleep src'),
            error_type=None,
        ),
        RuleCase(
            name='inferred-open-with-rests-on',
            draft=replace(
                create_draft(kind='open'), verdict='INFERRED', rests_on='a 4.x docs page'
            ),
            error_type=None,
        ),
        RuleCase(
            name='needs-analysis-open',
            draft=replace(create_draft(kind='open'), verdict='NEEDS-ANALYSIS'),
            error_type=None,
        ),
        RuleCase(
            name='blocked-open',
            draft=replace(create_draft(kind='open'), verdict='BLOCKED'),
            error_type=None,
        ),
    ]
    return as_params(cases)


def authority_rule_params() -> list[ParameterSet]:
    decision = create_valid_draft('decision')
    scout_open = create_draft(kind='open', source='scout')
    cases = [
        RuleCase(name='decision-from-the-owner', draft=decision, error_type=None),
        RuleCase(
            name='decision-from-a-scout',
            draft=replace(decision, source='scout'),
            error_type=DecisionSourceError,
        ),
        RuleCase(
            name='decision-from-the-primary',
            draft=replace(decision, source='primary'),
            error_type=DecisionSourceError,
        ),
        RuleCase(
            name='decision-from-the-owner-in-a-thread',
            draft=decision,
            thread='T1',
            error_type=DecisionInThreadError,
        ),
        RuleCase(
            name='decision-from-a-scout-in-a-thread',
            draft=replace(decision, source='scout'),
            thread='T1',
            error_type=DecisionInThreadError,
        ),
        RuleCase(
            name='owner-open-question-in-the-ledger',
            draft=replace(scout_open, source='user'),
            error_type=None,
        ),
        RuleCase(
            name='owner-open-question-in-a-thread',
            draft=replace(scout_open, source='user'),
            thread='T2',
            error_type=OwnerInThreadError,
        ),
        RuleCase(
            name='scout-open-question-in-a-thread',
            draft=scout_open,
            thread='T2',
            error_type=None,
        ),
    ]
    return as_params(cases)


def kind_rule_params() -> list[ParameterSet]:
    hypothesis = create_valid_draft('hypothesis')
    ruled_out = create_valid_draft('ruled_out')
    cases = [
        RuleCase(
            name='hypothesis-without-refute',
            draft=replace(hypothesis, refute=None),
            error_type=MissingRefuteError,
        ),
        RuleCase(name='hypothesis-with-refute', draft=hypothesis, error_type=None),
        RuleCase(
            name='ruled-out-without-cite-from-a-scout',
            draft=replace(ruled_out, cite=None),
            error_type=UncitedRuledOutError,
        ),
        RuleCase(
            name='ruled-out-without-cite-from-the-primary',
            draft=replace(ruled_out, cite=None, source='primary'),
            error_type=UncitedRuledOutError,
        ),
        RuleCase(name='ruled-out-with-cite', draft=ruled_out, error_type=None),
        RuleCase(
            name='ruled-out-by-the-owner-without-cite',
            draft=replace(ruled_out, cite=None, source='user'),
            error_type=None,
        ),
        RuleCase(
            name='ruled-out-by-the-owner-with-cite',
            draft=replace(ruled_out, cite=URL_CITE, source='user'),
            error_type=None,
        ),
    ]
    return as_params(cases)


def invalid_thread_params() -> list[ParameterSet]:
    names = {
        'lowercase': 't1',
        'zero': 'T0',
        'leading-zero': 'T01',
        'no-prefix': '1',
        'empty': '',
        'path-traversal': '../T1',
        'trailing-newline': 'T1\n',
        'dotted': 'T1.e1',
        'word': 'lead',
    }
    return as_labelled_params(names)
