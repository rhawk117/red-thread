"""The packaged outline: every required section is one of the sections, Acceptance among them."""

from typing import TYPE_CHECKING

import pytest
from red_thread_plans.domain import ACCEPTANCE
from red_thread_plans.packaged import load_outline

if TYPE_CHECKING:
    from red_thread_plans.domain import Outline


class TestOutline:
    @pytest.fixture
    def outline(self) -> Outline:
        return load_outline()

    def test_each_section_appears_once(self, outline: Outline) -> None:
        assert len(set(outline.sections)) == len(outline.sections)

    def test_every_required_section_is_a_section(self, outline: Outline) -> None:
        assert set(outline.required) <= set(outline.sections)

    def test_acceptance_is_required(self, outline: Outline) -> None:
        assert ACCEPTANCE in outline.required
