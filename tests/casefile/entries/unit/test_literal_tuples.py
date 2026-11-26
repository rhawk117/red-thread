"""Each hand-written tuple of names holds the names of its Literal alias, in the same order."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, get_args

import pytest
from red_thread_casefile.domain import (
    CASE_KINDS,
    ENTRY_KINDS,
    VERDICTS,
    CaseKind,
    EntryKind,
    Verdict,
)
from red_thread_casefile.lenses import LENS_NAMES, LensName
from red_thread_casefile.policy import CITE_STATES, CiteState

from tests.params import as_params

if TYPE_CHECKING:
    from typing import TypeAliasType


@dataclass(slots=True, kw_only=True, frozen=True)
class LiteralTuple:
    name: str
    names: tuple[str, ...]
    alias: TypeAliasType
    marks: tuple[pytest.MarkDecorator, ...] = ()


def literal_tuple_cases() -> pytest.MarkDecorator:
    pairs = [
        LiteralTuple(name='entry-kinds', names=ENTRY_KINDS, alias=EntryKind),
        LiteralTuple(name='verdicts', names=VERDICTS, alias=Verdict),
        LiteralTuple(name='case-kinds', names=CASE_KINDS, alias=CaseKind),
        LiteralTuple(name='lens-names', names=LENS_NAMES, alias=LensName),
        LiteralTuple(name='cite-states', names=CITE_STATES, alias=CiteState),
    ]
    return pytest.mark.parametrize('pair', as_params(pairs))


class TestLiteralTuples:
    @literal_tuple_cases()
    def test_the_tuple_holds_the_alias_names_in_order(self, pair: LiteralTuple) -> None:
        assert pair.names == get_args(pair.alias.__value__)
