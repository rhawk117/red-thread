"""Turns scenarios and labelled values into the parameter sets pytest.mark.parametrize takes."""

from typing import TYPE_CHECKING, Protocol, runtime_checkable

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from _pytest.mark import ParameterSet


@runtime_checkable
class Scenario(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def marks(self) -> tuple[pytest.MarkDecorator, ...]: ...


def to_param(case: Scenario) -> ParameterSet:
    return pytest.param(case, id=case.name, marks=case.marks)


def as_params(cases: Iterable[Scenario]) -> list[ParameterSet]:
    return list(map(to_param, cases))


def as_labelled_params(values: Mapping[str, object]) -> list[ParameterSet]:
    return [pytest.param(value, id=label) for label, value in values.items()]
