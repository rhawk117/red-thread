"""Scenarios for the finding rules: what check reports for a finding, and where."""

from dataclasses import dataclass
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

from tests.casefile.ledger.builders import URL_CITE, create_finding, create_valid_finding
from tests.params import as_labelled_params, as_params

if TYPE_CHECKING:
    import pytest
    from _pytest.mark import ParameterSet
    from red_thread_casefile.domain import CaseFinding
    from red_thread_casefile.errors import CaseFileError


@dataclass(slots=True, kw_only=True, frozen=True)
class RuleCase:
    name: str
    finding: CaseFinding
    error_types: tuple[type[CaseFileError], ...]
    thread: str | None = None
    marks: tuple[pytest.MarkDecorator, ...] = ()


def status_rule_params() -> list[ParameterSet]:
    known = create_valid_finding('known')
    question = create_finding(kind='open')
    cases = [
        RuleCase(
            name='known-without-cite',
            finding=known.replace_with(citation=None),
            error_types=(UncitedKnownError,),
        ),
        RuleCase(
            name='known-without-cite-or-verdict',
            finding=known.replace_with(citation=None, verdict=None),
            error_types=(UncitedKnownError,),
        ),
        RuleCase(
            name='known-inferred',
            finding=known.replace_with(verdict='INFERRED', rests_on='a 4.x docs page'),
            error_types=(UpgradedVerdictError,),
        ),
        RuleCase(
            name='known-needs-analysis',
            finding=known.replace_with(verdict='NEEDS-ANALYSIS'),
            error_types=(UpgradedVerdictError,),
        ),
        RuleCase(
            name='known-blocked',
            finding=known.replace_with(verdict='BLOCKED'),
            error_types=(UpgradedVerdictError,),
        ),
        RuleCase(
            name='inferred-open-without-rests-on',
            finding=question.replace_with(verdict='INFERRED'),
            error_types=(MissingRestsOnError,),
        ),
        RuleCase(
            name='inferred-hypothesis-without-rests-on',
            finding=create_valid_finding('hypothesis').replace_with(verdict='INFERRED'),
            error_types=(MissingRestsOnError,),
        ),
        RuleCase(name='known-verified', finding=known, error_types=()),
        RuleCase(
            name='known-with-no-verdict', finding=known.replace_with(verdict=None), error_types=()
        ),
        RuleCase(
            name='known-with-command-cite',
            finding=known.replace_with(citation='grep -rn sleep src'),
            error_types=(),
        ),
        RuleCase(
            name='inferred-open-with-rests-on',
            finding=question.replace_with(verdict='INFERRED', rests_on='a 4.x docs page'),
            error_types=(),
        ),
        RuleCase(
            name='needs-analysis-open',
            finding=question.replace_with(verdict='NEEDS-ANALYSIS'),
            error_types=(),
        ),
        RuleCase(
            name='blocked-open', finding=question.replace_with(verdict='BLOCKED'), error_types=()
        ),
    ]
    return as_params(cases)


def authority_rule_params() -> list[ParameterSet]:
    decision = create_valid_finding('decision')
    scout_open = create_finding(kind='open', source='scout')
    cases = [
        RuleCase(name='decision-from-the-owner', finding=decision, error_types=()),
        RuleCase(
            name='decision-from-a-scout',
            finding=decision.replace_with(source='scout'),
            error_types=(DecisionSourceError,),
        ),
        RuleCase(
            name='decision-from-the-primary',
            finding=decision.replace_with(source='primary'),
            error_types=(DecisionSourceError,),
        ),
        RuleCase(
            name='decision-from-the-owner-in-a-thread',
            finding=decision,
            thread='T1',
            error_types=(DecisionInThreadError,),
        ),
        RuleCase(
            name='decision-from-a-scout-in-a-thread',
            finding=decision.replace_with(source='scout'),
            thread='T1',
            error_types=(DecisionInThreadError,),
        ),
        RuleCase(
            name='owner-open-question-in-the-case-file',
            finding=scout_open.replace_with(source='user'),
            error_types=(),
        ),
        RuleCase(
            name='owner-open-question-in-a-thread',
            finding=scout_open.replace_with(source='user'),
            thread='T2',
            error_types=(OwnerInThreadError,),
        ),
        RuleCase(
            name='scout-open-question-in-a-thread', finding=scout_open, thread='T2', error_types=()
        ),
    ]
    return as_params(cases)


def kind_rule_params() -> list[ParameterSet]:
    hypothesis = create_valid_finding('hypothesis')
    ruled_out = create_valid_finding('ruled_out')
    cases = [
        RuleCase(
            name='hypothesis-without-refute',
            finding=hypothesis.replace_with(refuted_if=None),
            error_types=(MissingRefuteError,),
        ),
        RuleCase(name='hypothesis-with-refute', finding=hypothesis, error_types=()),
        RuleCase(
            name='ruled-out-without-cite-from-a-scout',
            finding=ruled_out.replace_with(citation=None),
            error_types=(UncitedRuledOutError,),
        ),
        RuleCase(
            name='ruled-out-without-cite-from-the-primary',
            finding=ruled_out.replace_with(citation=None, source='primary'),
            error_types=(UncitedRuledOutError,),
        ),
        RuleCase(name='ruled-out-with-cite', finding=ruled_out, error_types=()),
        RuleCase(
            name='ruled-out-by-the-owner-without-cite',
            finding=ruled_out.replace_with(citation=None, source='user'),
            error_types=(),
        ),
        RuleCase(
            name='ruled-out-by-the-owner-with-cite',
            finding=ruled_out.replace_with(citation=URL_CITE, source='user'),
            error_types=(),
        ),
    ]
    return as_params(cases)


def combined_rule_params() -> list[ParameterSet]:
    cases = [
        RuleCase(
            name='claim-and-kind-faults-are-both-reported',
            finding=create_finding(kind='hypothesis', verdict='INFERRED'),
            error_types=(MissingRestsOnError, MissingRefuteError),
        ),
        RuleCase(
            name='claim-and-authority-faults-are-both-reported',
            finding=create_finding(kind='known', source='user'),
            thread='T1',
            error_types=(UncitedKnownError, OwnerInThreadError),
        ),
        RuleCase(
            name='authority-and-kind-faults-are-both-reported',
            finding=create_finding(kind='hypothesis', source='user'),
            thread='T1',
            error_types=(OwnerInThreadError, MissingRefuteError),
        ),
    ]
    return as_params(cases)


def stray_thread_file_params() -> list[ParameterSet]:
    names = {
        'lowercase': 't1',
        'zero': 'T0',
        'leading-zero': 'T01',
        'no-prefix': '1',
        'dotted': 'T1.e1',
        'word': 'lead',
    }
    return as_labelled_params(names)
