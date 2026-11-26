"""What makes a draft storable and a citation still trustworthy."""

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
    MissingRefuteError,
    MissingRestsOnError,
    OwnerInThreadError,
    UncitedKnownError,
    UncitedRuledOutError,
    UnknownSupersededError,
    UpgradedVerdictError,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from red_thread_casefile.domain import Draft

type CiteState = Literal['ok', 'moved', 'changed', 'missing', 'unchecked']
type ClaimProblem = UpgradedVerdictError | UncitedKnownError | MissingRestsOnError
type AuthorityProblem = DecisionInThreadError | DecisionSourceError | OwnerInThreadError
type KindProblem = MissingRefuteError | UncitedRuledOutError
type DraftProblem = ClaimProblem | AuthorityProblem | KindProblem
type SupersedeProblem = UnknownSupersededError | ForeignSupersededError

CITE_STATES: tuple[CiteState, ...] = ('ok', 'moved', 'changed', 'missing', 'unchecked')
FAILING_STATES: tuple[CiteState, ...] = ('changed', 'missing')
QUIET_STATES: tuple[CiteState, ...] = ('ok', 'unchecked')


@dataclass(slots=True, kw_only=True, frozen=True)
class DraftPolicy:
    draft: Draft
    thread: str | None = None

    @property
    def has_cite(self) -> bool:
        return self.draft.cite is not None

    @property
    def is_from_owner(self) -> bool:
        return self.draft.source == OWNER

    @property
    def is_upgraded(self) -> bool:
        return self.draft.kind == 'known' and self.draft.verdict not in {None, 'VERIFIED'}

    @property
    def lacks_caveat(self) -> bool:
        return self.draft.verdict == 'INFERRED' and self.draft.rests_on is None

    def get_claim_problem(self) -> ClaimProblem | None:
        if self.is_upgraded:
            return UpgradedVerdictError(
                position=self.draft.position, verdict=self.draft.verdict or ''
            )

        if self.draft.kind == 'known' and not self.has_cite:
            return UncitedKnownError(position=self.draft.position)

        if self.lacks_caveat:
            return MissingRestsOnError(position=self.draft.position)

        return None

    def get_authority_problem(self) -> AuthorityProblem | None:
        if self.draft.kind == 'decision' and self.thread is not None:
            return DecisionInThreadError(position=self.draft.position, thread=self.thread)

        if self.draft.kind == 'decision' and not self.is_from_owner:
            return DecisionSourceError(position=self.draft.position, source=self.draft.source)

        if self.is_from_owner and self.thread is not None:
            return OwnerInThreadError(position=self.draft.position, thread=self.thread)

        return None

    def get_kind_problem(self) -> KindProblem | None:
        if self.draft.kind == 'hypothesis' and self.draft.refute is None:
            return MissingRefuteError(position=self.draft.position)

        if self.draft.kind != 'ruled_out':
            return None

        if not self.has_cite and not self.is_from_owner:
            return UncitedRuledOutError(position=self.draft.position)

        return None

    def get_storage_problem(self) -> DraftProblem | None:
        return self.get_claim_problem() or self.get_authority_problem() or self.get_kind_problem()


@dataclass(slots=True, kw_only=True, frozen=True)
class SupersedePolicy:
    draft: Draft
    known_refs: frozenset[str]
    thread: str | None = None

    @property
    def unknown_ref(self) -> str | None:
        return next((ref for ref in self.draft.supersedes if ref not in self.known_refs), None)

    @property
    def foreign_ref(self) -> str | None:
        if self.thread is None:
            return None
        prefix = f'{self.thread}.'
        return next((ref for ref in self.draft.supersedes if not ref.startswith(prefix)), None)

    def get_supersede_problem(self) -> SupersedeProblem | None:
        if (unknown := self.unknown_ref) is not None:
            return UnknownSupersededError(position=self.draft.position, ref=unknown)

        foreign = self.foreign_ref
        if foreign is not None and self.thread is not None:
            return ForeignSupersededError(
                position=self.draft.position, ref=foreign, thread=self.thread
            )

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


def get_page_problem(url: str) -> InvalidPageUrlError | None:
    if url.startswith(PAGE_URL_SCHEME) and not any(map(str.isspace, url)):
        return None
    return InvalidPageUrlError(url=url)
