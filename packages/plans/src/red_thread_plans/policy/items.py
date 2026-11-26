"""What makes one ticket or one risk of a drafted plan storable: every promise traced."""

from collections import Counter
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from red_thread_plans.domain import (
    RESTING_KINDS,
    RISK_ID,
    SLUG,
    Mitigate,
    Sentence,
    YouIntervene,
)
from red_thread_plans.errors import (
    BlankPlanTextError,
    EmptyRecutError,
    GroundlessAcceptanceError,
    InvalidOwnedPathError,
    InvalidPlanIdError,
    MissingAcceptanceError,
    MissingOwnsError,
    RetiredRestingRefError,
    StrayRecutError,
    UnfitRestingRefError,
    UnknownRestingRefError,
    UnknownRiskTicketError,
    UnlistedCriterionError,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from red_thread_casefile.domain import Entry, Ledger
    from red_thread_casefile.errors import CaseFileError

    from red_thread_plans.domain import Acceptance, Risk, TicketDraft

type RestingProblem = UnknownRestingRefError | RetiredRestingRefError | UnfitRestingRefError
type Problems = tuple[CaseFileError, ...]

SLUG_HINT = 'a slug such as plan-record'
RISK_HINT = 'R1, R2 and so on'


def describe_owned_fault(owned: str) -> str | None:
    path = PurePosixPath(owned)
    if not owned.strip():
        return 'is empty'

    if path.is_absolute():
        return 'is absolute'

    if '..' in path.parts:
        return 'climbs out with ..'

    if '[' in owned or ']' in owned:
        return 'uses a [ ] class'

    return None


def get_owned_problem(ticket: str, owned: str) -> InvalidOwnedPathError | None:
    reason = describe_owned_fault(owned)
    if reason is None:
        return None
    return InvalidOwnedPathError(ticket=ticket, owned=owned, reason=reason)


def get_blank_problems(field: str, texts: Iterable[str]) -> Problems:
    numbered = enumerate(texts, 1)
    return tuple(
        BlankPlanTextError(field=f'{field} {number}')
        for number, text in numbered
        if not text.strip()
    )


def find_duplicates(values: Iterable[str]) -> tuple[str, ...]:
    counted = Counter(values)
    return tuple(value for value, count in counted.items() if count > 1)


@dataclass(slots=True, kw_only=True, frozen=True)
class Grounds:
    live: Mapping[str, Entry]
    known: frozenset[str]

    def get_ref_problem(self, sentence: Sentence, ref: str) -> RestingProblem | None:
        if ref not in self.known:
            return UnknownRestingRefError(sentence=sentence, ref=ref)

        entry = self.live.get(ref)
        if entry is None:
            return RetiredRestingRefError(sentence=sentence, ref=ref)

        if entry.kind not in RESTING_KINDS:
            return UnfitRestingRefError(sentence=sentence, ref=ref, kind=entry.kind)

        return None

    def get_sentence_problem(
        self, sentence: Sentence, acceptance: Acceptance
    ) -> CaseFileError | None:
        if not acceptance.criterion.strip():
            return BlankPlanTextError(field=sentence.label)

        if not acceptance.required_by:
            return GroundlessAcceptanceError(sentence=sentence)

        found = (self.get_ref_problem(sentence, ref) for ref in acceptance.required_by)
        return next(filter(None, found), None)


def create_grounds(ledger: Ledger) -> Grounds:
    return Grounds(live={entry.ref: entry for entry in ledger.live}, known=ledger.refs)


@dataclass(slots=True, kw_only=True, frozen=True)
class TicketPolicy:
    ticket: TicketDraft
    grounds: Grounds

    def get_label_problem(self) -> CaseFileError | None:
        if not SLUG.fullmatch(self.ticket.id):
            return InvalidPlanIdError(field='ticket id', value=self.ticket.id, expected=SLUG_HINT)

        if not SLUG.fullmatch(self.ticket.worktree):
            return InvalidPlanIdError(
                field='worktree', value=self.ticket.worktree, expected=SLUG_HINT
            )

        if not self.ticket.title.strip():
            return BlankPlanTextError(field=f'ticket {self.ticket.id} title')

        if not self.ticket.why.strip():
            return BlankPlanTextError(field=f'ticket {self.ticket.id} why')

        return None

    def get_scope_problem(self) -> CaseFileError | None:
        if not self.ticket.acceptance:
            return MissingAcceptanceError(ticket=self.ticket.id)

        if not self.ticket.owns:
            return MissingOwnsError(ticket=self.ticket.id)

        found = (get_owned_problem(self.ticket.id, owned) for owned in self.ticket.owns)
        return next(filter(None, found), None)

    def get_ticket_issues(self) -> Problems:
        numbered = enumerate(self.ticket.acceptance, 1)
        sentences = (
            self.grounds.get_sentence_problem(Sentence(ticket=self.ticket.id, number=number), item)
            for number, item in numbered
        )
        found = (self.get_label_problem(), self.get_scope_problem(), *sentences)
        return tuple(filter(None, found))


@dataclass(slots=True, kw_only=True, frozen=True)
class RiskPolicy:
    risk: Risk
    tickets: Mapping[str, TicketDraft]

    def get_label_problem(self) -> CaseFileError | None:
        if not RISK_ID.fullmatch(self.risk.id):
            return InvalidPlanIdError(field='risk id', value=self.risk.id, expected=RISK_HINT)

        if not self.risk.risk.strip():
            return BlankPlanTextError(field=f'risk {self.risk.id}')

        if not self.risk.signal.strip():
            return BlankPlanTextError(field=f'risk {self.risk.id} signal')

        return None

    def find_unknown(self, names: Iterable[str]) -> UnknownRiskTicketError | None:
        unknown = next((name for name in names if name not in self.tickets), None)
        if unknown is None:
            return None
        return UnknownRiskTicketError(risk=self.risk.id, ticket=unknown)

    def get_mitigation_problem(self, handling: Mitigate) -> CaseFileError | None:
        if problem := self.find_unknown((handling.ticket,)):
            return problem

        criterion = handling.criterion
        texts = {item.criterion for item in self.tickets[handling.ticket].acceptance}
        if criterion is None or criterion in texts:
            return None
        return UnlistedCriterionError(
            risk=self.risk.id, ticket=handling.ticket, criterion=criterion
        )

    def get_recut_problem(self, handling: YouIntervene) -> CaseFileError | None:
        if not handling.recut:
            return EmptyRecutError(risk=self.risk.id)

        if problem := self.find_unknown(handling.recut):
            return problem

        stray = next((name for name in handling.recut if name not in self.risk.tickets), None)
        if stray is None:
            return None
        return StrayRecutError(risk=self.risk.id, ticket=stray)

    def get_handling_problem(self) -> CaseFileError | None:
        handling = self.risk.handling
        if isinstance(handling, Mitigate):
            return self.get_mitigation_problem(handling)

        if isinstance(handling, YouIntervene):
            return self.get_recut_problem(handling)

        return None

    def get_risk_issues(self) -> Problems:
        found = (
            self.get_label_problem(),
            self.find_unknown(self.risk.tickets),
            self.get_handling_problem(),
        )
        return tuple(filter(None, found))
