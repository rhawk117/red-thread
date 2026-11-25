"""Mapping a Rust directory: a struct used in another file outranks one nothing uses."""

from typing import TYPE_CHECKING

import pytest
from red_thread_navigate.cli import create_navigator

from tests.navigate.symbols.samples import SourceDir

if TYPE_CHECKING:
    from pathlib import Path

MODELS = """\
pub struct Unused {
    pub id: u32,
}

pub struct Shared {
    pub id: u32,
}
"""
CLIENT = """\
use crate::models::Shared;

pub fn build() -> Shared {
    let first: Shared = Shared { id: 1 };
    first
}

pub fn keep(value: Shared) -> Shared {
    value
}
"""
BIG_BUDGET = 10_000
NAVIGATOR = create_navigator()


class TestRustRanking:
    @pytest.fixture
    def project(self, tmp_path: Path) -> SourceDir:
        source = SourceDir(root=tmp_path)
        source.write('models.rs', MODELS)
        source.write('client.rs', CLIENT)
        return source

    def test_struct_used_in_another_file_precedes_a_struct_nothing_uses(
        self, project: SourceDir
    ) -> None:
        text = NAVIGATOR.map(project.root, budget=BIG_BUDGET)

        assert text.index('models.rs#Shared') < text.index('models.rs#Unused')
