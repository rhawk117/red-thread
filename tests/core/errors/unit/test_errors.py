"""Every package's failures derive from the one shared base, RedThreadError."""

import pytest
from red_thread_casefile.errors import CaseFileError
from red_thread_core.errors import RedThreadError
from red_thread_plans.errors import PlanError


def package_error_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        'error_type',
        [
            pytest.param(CaseFileError, id='casefile'),
            pytest.param(PlanError, id='plans'),
        ],
    )


@package_error_cases()
def test_package_error_derives_from_the_shared_base(error_type: type[Exception]) -> None:
    assert issubclass(error_type, RedThreadError)
