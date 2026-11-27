"""What makes an entry sound and a citation still trustworthy."""

from collections import Counter
from dataclasses import dataclass
from operator import attrgetter
from typing import TYPE_CHECKING, Literal

from red_thread_core.util import squeeze

from red_thread_casefile.domain import OWNER, PAGE_URL_SCHEME
from red_thread_casefile.errors import (
    DecisionInThreadError,
    DecisionSourceError,
    ForeignSupersededError,
    InvalidPageUrlError,
    MisquotedCiteError,
    MissingQuoteError,
    MissingRefuteError,
    MissingRestsOnError,
    OwnerInThreadError,
    UncitedKnownError,
    UncitedRuledOutError,
    UnknownSupersededError,
    UnresolvedCiteError,
    UpgradedVerdictError,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from red_thread_casefile.domain import Entry, Spot
    from red_thread_casefile.errors import CaseFileError

type CiteState = Literal['ok', 'moved', 'changed', 'missing', 'unchecked']
type ClaimProblem = UpgradedVerdictError | UncitedKnownError | MissingRestsOnError
type AuthorityProblem = DecisionInThreadError | DecisionSourceError | OwnerInThreadError
type KindProblem = MissingRefuteError | UncitedRuledOutError
type EntryProblem = ClaimProblem | AuthorityProblem | KindProblem
type SupersedeProblem = UnknownSupersededError | ForeignSupersededError
type QuoteProblem = UnresolvedCiteError | MissingQuoteError
type DriftProblem = UnresolvedCiteError | MisquotedCiteError

CITE_STATES: tuple[CiteState, ...] = ('ok', 'moved', 'changed', 'missing', 'unchecked')
FAILING_STATES: tuple[CiteState, ...] = ('changed', 'missing')
QUIET_STATES: tuple[CiteState, ...] = ('ok', 'unchecked')
MISPLACED_STATES: tuple[CiteState, ...] = ('changed', 'moved')


@dataclass(slots=True, kw_only=True, frozen=True)
class EntryPolicy:
    entry: Entry
    spot: Spot

    @property
    def thread(self) -> str | None:
        return self.entry.thread

    @property
    def has_cite(self) -> bool:
        return self.entry.cite is not None

    @property
    def is_from_owner(self) -> bool:
        return self.entry.source == OWNER

    @property
    def is_upgraded(self) -> bool:
        return self.entry.kind == 'known' and self.entry.verdict not in {None, 'VERIFIED'}

    @property
    def lacks_caveat(self) -> bool:
        return self.entry.verdict == 'INFERRED' and self.entry.rests_on is None

    def get_claim_problem(self) -> ClaimProblem | None:
        if self.is_upgraded:
            return UpgradedVerdictError(spot=self.spot, verdict=self.entry.verdict or '')

        if self.entry.kind == 'known' and not self.has_cite:
            return UncitedKnownError(spot=self.spot)

        if self.lacks_caveat:
            return MissingRestsOnError(spot=self.spot)

        return None

    def get_authority_problem(self) -> AuthorityProblem | None:
        if self.entry.kind == 'decision' and self.thread is not None:
            return DecisionInThreadError(spot=self.spot, thread=self.thread)

        if self.entry.kind == 'decision' and not self.is_from_owner:
            return DecisionSourceError(spot=self.spot, source=self.entry.source)

        if self.is_from_owner and self.thread is not None:
            return OwnerInThreadError(spot=self.spot, thread=self.thread)

        return None

    def get_kind_problem(self) -> KindProblem | None:
        if self.entry.kind == 'hypothesis' and self.entry.refute is None:
            return MissingRefuteError(spot=self.spot)

        if self.entry.kind != 'ruled_out':
            return None

        if not self.has_cite and not self.is_from_owner:
            return UncitedRuledOutError(spot=self.spot)

        return None

    def get_entry_issues(self) -> tuple[EntryProblem, ...]:
        found = (self.get_claim_problem(), self.get_authority_problem(), self.get_kind_problem())
        return tuple(filter(None, found))


@dataclass(slots=True, kw_only=True, frozen=True)
class SupersedePolicy:
    entry: Entry
    spot: Spot
    known_refs: frozenset[str]

    @property
    def thread(self) -> str | None:
        return self.entry.thread

    @property
    def unknown_ref(self) -> str | None:
        return next((ref for ref in self.entry.supersedes if ref not in self.known_refs), None)

    @property
    def foreign_ref(self) -> str | None:
        if self.thread is None:
            return None
        prefix = f'{self.thread}.'
        return next((ref for ref in self.entry.supersedes if not ref.startswith(prefix)), None)

    def get_supersede_problem(self) -> SupersedeProblem | None:
        if (unknown := self.unknown_ref) is not None:
            return UnknownSupersededError(spot=self.spot, ref=unknown)

        foreign = self.foreign_ref
        if foreign is not None and self.thread is not None:
            return ForeignSupersededError(spot=self.spot, ref=foreign, thread=self.thread)

        return None


@dataclass(slots=True, kw_only=True, frozen=True)
class Finding:
    ref: str
    cite: str
    state: CiteState
    moved_to: int | None = None


def tally_states(findings: Iterable[Finding]) -> Counter[CiteState]:
    return Counter(map(attrgetter('state'), findings))


@dataclass(slots=True, kw_only=True, frozen=True)
class CiteCheck:
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

    def get_state(self) -> CiteState:
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
class CitePolicy:
    entry: Entry
    spot: Spot
    probe: CiteCheck
    is_fresh: bool

    @property
    def cite(self) -> str:
        return self.entry.cite or ''

    def get_quote_problem(self) -> QuoteProblem | None:
        if self.entry.quote is not None:
            return None

        cited = self.probe.cited_line
        if cited is None:
            return UnresolvedCiteError(spot=self.spot, cite=self.cite)

        return MissingQuoteError(spot=self.spot, cite=self.cite, line=cited)

    def get_drift_problem(self) -> DriftProblem | None:
        if not self.is_fresh:
            return None

        if self.probe.cited_line is None:
            return UnresolvedCiteError(spot=self.spot, cite=self.cite)

        if self.probe.get_state() in MISPLACED_STATES:
            return MisquotedCiteError(spot=self.spot, cite=self.cite, found_at=self.probe.moved_to)

        return None

    def get_cite_problem(self) -> CaseFileError | None:
        return self.get_quote_problem() or self.get_drift_problem()


def get_page_problem(url: str) -> InvalidPageUrlError | None:
    if url.startswith(PAGE_URL_SCHEME) and not any(map(str.isspace, url)):
        return None
    return InvalidPageUrlError(url=url)
