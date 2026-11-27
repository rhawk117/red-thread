"""The packaged wording and lenses: complete for every kind and name, and strict about keys."""

from typing import get_args

import pytest
from red_thread_casefile.documents import NoteKind, Wording
from red_thread_casefile.domain import ENTRY_KINDS
from red_thread_casefile.lenses import LENS_NAMES, LensBook
from red_thread_casefile.packaged import (
    CASEFILE_PACKAGE,
    WORDING_FILE,
    load_lens_book,
    load_wording,
)
from red_thread_core.errors import MalformedDocumentError
from red_thread_core.packaged import load_asset

from tests.codec import YAML

WORDING_WITH_UNKNOWN_KEY = b"""
headings: []
prefixes: {}
map_note: a map
retired_note: retired
terms: []
glossary: []
"""
PART_WITH_UNKNOWN_KEY = b"""
reading: []
lenses:
  - name: brief
    intro: Brief of
    budget: 60
    parts:
      - {title: Open, knd: open}
"""


class TestWording:
    @pytest.fixture
    def wording(self) -> Wording:
        return load_wording()

    def test_every_entry_kind_has_one_heading(self, wording: Wording) -> None:
        assert sorted(heading.kind for heading in wording.headings) == sorted(ENTRY_KINDS)

    def test_every_note_kind_has_a_prefix(self, wording: Wording) -> None:
        assert set(wording.prefixes) == set(get_args(NoteKind.__value__))

    def test_a_note_is_its_prefix_then_its_value(self, wording: Wording) -> None:
        assert wording.write_note('rests_on', 'a page').text == 'rests on: a page'

    def test_an_unknown_key_is_refused(self) -> None:
        assert isinstance(YAML.decode(WORDING_WITH_UNKNOWN_KEY, Wording), MalformedDocumentError)

    def test_a_file_of_another_shape_is_refused(self) -> None:
        with pytest.raises(MalformedDocumentError):
            load_asset(CASEFILE_PACKAGE, WORDING_FILE, LensBook)


class TestLensBook:
    @pytest.fixture
    def book(self) -> LensBook:
        return load_lens_book()

    def test_every_lens_name_has_one_lens(self, book: LensBook) -> None:
        assert sorted(lens.name for lens in book.lenses) == sorted(LENS_NAMES)

    def test_every_part_shows_either_a_kind_or_a_fixed_block(self, book: LensBook) -> None:
        parts = (part for lens in book.lenses for part in lens.parts)
        assert all((part.kind is None) != (part.fixed is None) for part in parts)

    def test_an_unknown_part_key_is_refused(self) -> None:
        assert isinstance(YAML.decode(PART_WITH_UNKNOWN_KEY, LensBook), MalformedDocumentError)
