"""Finding a name in a memory source tree: the verb reads files only through its injected seam."""

import pytest
from red_thread_navigate.services import Navigator
from red_thread_navigate.symbols.store import RegistryBackends
from red_thread_navigate.walk import PathMissingError, SourceTree

from tests.navigate.samples import BIG_BUDGET
from tests.navigate.walk.memory import MemoryTree

CORE = 'def helper():\n    return 1\n'
CLIENT = 'from core import helper\n\n\ndef run():\n    helper()\n'


class TestFindInMemory:
    @pytest.fixture
    def tree(self) -> MemoryTree:
        return MemoryTree(texts={'core.py': CORE, 'client.py': CLIENT})

    @pytest.fixture
    def navigator(self, tree: MemoryTree) -> Navigator:
        return Navigator(tree=tree, backends=RegistryBackends())

    def test_the_fake_satisfies_the_source_tree_protocol(self, tree: MemoryTree) -> None:
        assert isinstance(tree, SourceTree)

    def test_a_definition_and_its_reference_are_found_without_disk(
        self, navigator: Navigator, tree: MemoryTree
    ) -> None:
        text = navigator.find('helper', tree.root, budget=BIG_BUDGET)

        assert 'core.py' in text
        assert 'client.py' in text

    def test_a_name_nothing_defines_reports_no_match(
        self, navigator: Navigator, tree: MemoryTree
    ) -> None:
        text = navigator.find('missing', tree.root, budget=BIG_BUDGET)

        assert 'missing' in text
        assert 'core.py' not in text

    def test_a_root_the_tree_does_not_hold_is_refused(
        self, navigator: Navigator, tree: MemoryTree
    ) -> None:
        with pytest.raises(PathMissingError):
            navigator.find('helper', tree.root / 'elsewhere', budget=BIG_BUDGET)
