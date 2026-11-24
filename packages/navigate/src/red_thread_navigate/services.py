"""The navigator: the three verbs over one source tree and one set of language backends."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_navigate.find.services import find_name
from red_thread_navigate.map.services import map_path
from red_thread_navigate.slice.services import Slicer
from red_thread_navigate.symbols.services import index_path

if TYPE_CHECKING:
    from pathlib import Path

    from red_thread_navigate.symbols.domain import Backends
    from red_thread_navigate.walk import SourceTree


@dataclass(slots=True, kw_only=True, frozen=True)
class Navigator:
    tree: SourceTree
    backends: Backends

    def map(self, path: Path, *, budget: int) -> str:
        index = index_path(path, tree=self.tree, backends=self.backends)
        return map_path(index, self.backends, budget=budget)

    def find(self, name: str, path: Path, *, budget: int) -> str:
        index = index_path(path, tree=self.tree, backends=self.backends)
        return find_name(index, name, budget=budget)

    def slice(self, text: str, *, root: Path, budget: int) -> str:
        slicer = Slicer(tree=self.tree, backends=self.backends)
        return slicer.slice_address(text, root=root, budget=budget)
