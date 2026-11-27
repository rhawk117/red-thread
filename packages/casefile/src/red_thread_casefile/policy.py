"""What makes a finding sound and a citation still trustworthy."""

from collections import Counter
from dataclasses import dataclass
from operator import attrgetter
from typing import TYPE_CHECKING, Literal

from red_thread_core.dto import DTO
from red_thread_core.util import squeeze

from red_thread_casefile.domain import OWNER, PAGE_URL_SCHEME
from red_thread_casefile.errors import (
    DecisionInThreadError,
    DecisionSourceError,
    ForeignSupersededError,
    InvalidPageUrlError,
    MisquotedCitationError,
    MissingQuoteError,
    MissingRefuteError,
    MissingRestsOnError,
    OwnerInThreadError,
    UncitedKnownError,
    UncitedRuledOutError,
    UnknownSupersededError,
    UnresolvedCitationError,
    UpgradedVerdictError,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from red_thread_casefile.domain import CaseFinding, FindingLocation
    from red_thread_casefile.errors import CaseFileError

type CitationState = Literal['ok', 'moved', 'changed', 'missing', 'unchecked']
type ClaimProblem = UpgradedVerdictError | UncitedKnownError | MissingRestsOnError
type AuthorityProblem = DecisionInThreadError | DecisionSourceError | OwnerInThreadError
type KindProblem = MissingRefuteError | UncitedRuledOutError
type FindingProblem = ClaimProblem | AuthorityProblem | KindProblem
type SupersedeProblem = UnknownSupersededError | ForeignSupersededError
type QuoteProblem = UnresolvedCitationError | MissingQuoteError
type DriftProblem = UnresolvedCitationError | MisquotedCitationError

CITE_STATES: tuple[CitationState, ...] = ('ok', 'moved', 'changed', 'missing', 'unchecked')
FAILING_STATES: tuple[CitationState, ...] = ('changed', 'missing')
QUIET_STATES: tuple[CitationState, ...] = ('ok', 'unchecked')
MISPLACED_STATES: tuple[CitationState, ...] = ('changed', 'moved')


@dataclass(slots=True, kw_only=True, frozen=True)
class FindingPolicy:
    finding: CaseFinding
    location: FindingLocation

    @property
    def thread(self) -> str | None:
        return self.finding.thread

    @property
    def has_citation(self) -> bool:
        return self.finding.citation is not None

    @property
    def is_from_owner(self) -> bool:
        return self.finding.source == OWNER

    @property
    def is_upgraded(self) -> bool:
        return self.finding.kind == 'known' and self.finding.verdict not in {None, 'VERIFIED'}

    @property
    def lacks_caveat(self) -> bool:
        return self.finding.verdict == 'INFERRED' and self.finding.rests_on is None

    def get_claim_problem(self) -> ClaimProblem | None:
        if self.is_upgraded:
            return UpgradedVerdictError(location=self.location, verdict=self.finding.verdict or '')

        if self.finding.kind == 'known' and not self.has_citation:
            return UncitedKnownError(location=self.location)

        if self.lacks_caveat:
            return MissingRestsOnError(location=self.location)

        return None

    def get_authority_problem(self) -> AuthorityProblem | None:
        if self.finding.kind == 'decision' and self.thread is not None:
            return DecisionInThreadError(location=self.location, thread=self.thread)

        if self.finding.kind == 'decision' and not self.is_from_owner:
            return DecisionSourceError(location=self.location, source=self.finding.source)

        if self.is_from_owner and self.thread is not None:
            return OwnerInThreadError(location=self.location, thread=self.thread)

        return None

    def get_kind_problem(self) -> KindProblem | None:
        if self.finding.kind == 'hypothesis' and self.finding.refuted_if is None:
            return MissingRefuteError(location=self.location)

        if self.finding.kind != 'ruled_out':
            return None

        if not self.has_citation and not self.is_from_owner:
            return UncitedRuledOutError(location=self.location)

        return None

    def get_finding_issues(self) -> tuple[FindingProblem, ...]:
        found = (self.get_claim_problem(), self.get_authority_problem(), self.get_kind_problem())
        return tuple(filter(None, found))


@dataclass(slots=True, kw_only=True, frozen=True)
class SupersedePolicy:
    finding: CaseFinding
    location: FindingLocation
    known_finding_ids: frozenset[str]

    @property
    def thread(self) -> str | None:
        return self.finding.thread

    @property
    def unknown_finding_id(self) -> str | None:
        return next(
            (
                finding_id
                for finding_id in self.finding.supersedes
                if finding_id not in self.known_finding_ids
            ),
            None,
        )

    @property
    def foreign_finding_id(self) -> str | None:
        if self.thread is None:
            return None
        prefix = f'{self.thread}.'
        return next(
            (
                finding_id
                for finding_id in self.finding.supersedes
                if not finding_id.startswith(prefix)
            ),
            None,
        )

    def get_supersede_problem(self) -> SupersedeProblem | None:
        if (unknown := self.unknown_finding_id) is not None:
            return UnknownSupersededError(location=self.location, finding_id=unknown)

        foreign = self.foreign_finding_id
        if foreign is not None and self.thread is not None:
            return ForeignSupersededError(
                location=self.location, finding_id=foreign, thread=self.thread
            )

        return None


class CitationCheck(DTO, frozen=True, kw_only=True, gc=False):
    finding_id: str
    citation: str
    state: CitationState
    moved_to: int | None = None


def tally_states(citation_checks: Iterable[CitationCheck]) -> Counter[CitationState]:
    return Counter(map(attrgetter('state'), citation_checks))


@dataclass(slots=True, kw_only=True, frozen=True)
class CitationReader:
    quote: str
    line: int
    lines: tuple[str, ...] | None

    @property
    def wanted(self) -> str:
        return squeeze(self.quote)

    @property
    def cited_line(self) -> str | None:
        if self.lines is None or not 1 <= self.line <= len(self.lines):
            return None
        return self.lines[self.line - 1].strip()

    @property
    def is_in_place(self) -> bool:
        cited = self.cited_line
        return cited is not None and self.holds(cited)

    @property
    def moved_to(self) -> int | None:
        if self.is_in_place or not self.wanted:
            return None
        numbered = enumerate(self.lines or (), 1)
        return next((number for number, text in numbered if self.holds(text)), None)

    def holds(self, text: str) -> bool:
        found = squeeze(text)
        if not self.wanted:
            return not found
        return self.wanted in found

    def get_state(self) -> CitationState:
        if self.lines is None:
            return 'missing'

        if self.is_in_place:
            return 'ok'

        if self.moved_to is not None:
            return 'moved'

        if self.cited_line is None:
            return 'missing'

        return 'changed'


@dataclass(slots=True, kw_only=True, frozen=True)
class CitationPolicy:
    finding: CaseFinding
    location: FindingLocation
    probe: CitationReader
    is_fresh: bool

    @property
    def citation(self) -> str:
        return self.finding.citation or ''

    def get_quote_problem(self) -> QuoteProblem | None:
        if self.finding.quote is not None:
            return None

        cited = self.probe.cited_line
        if cited is None:
            return UnresolvedCitationError(location=self.location, citation=self.citation)

        return MissingQuoteError(location=self.location, citation=self.citation, line=cited)

    def get_drift_problem(self) -> DriftProblem | None:
        if not self.is_fresh:
            return None

        if self.probe.cited_line is None:
            return UnresolvedCitationError(location=self.location, citation=self.citation)

        if self.probe.get_state() in MISPLACED_STATES:
            return MisquotedCitationError(
                location=self.location, citation=self.citation, found_at=self.probe.moved_to
            )

        return None

    def get_citation_problem(self) -> CaseFileError | None:
        return self.get_quote_problem() or self.get_drift_problem()


def get_page_problem(url: str) -> InvalidPageUrlError | None:
    if url.startswith(PAGE_URL_SCHEME) and not any(map(str.isspace, url)):
        return None
    return InvalidPageUrlError(url=url)
