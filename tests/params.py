"""Turns scenarios and labelled values into the parameter sets pytest.mark.parametrize takes."""

from operator import attrgetter
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from _pytest.mark import ParameterSet


@runtime_checkable
class HasParam(Protocol):
    @property
    def param(self) -> ParameterSet: ...


def as_params(cases: Iterable[HasParam]) -> list[ParameterSet]:
    return list(map(attrgetter('param'), cases))


def as_labelled_params(values: Mapping[str, object]) -> list[ParameterSet]:
    return [pytest.param(value, id=label) for label, value in values.items()]
