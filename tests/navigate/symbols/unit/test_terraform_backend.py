"""The Terraform backend names blocks and references the way Terraform addresses them."""

from importlib import resources
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import pytest
from red_thread_navigate.find.services import references_to
from red_thread_navigate.symbols.store import TERRAFORM_BACKEND, backend_for
from red_thread_navigate.walk import SourceFile

from tests.navigate.symbols.samples import TERRAFORM_BROKEN, TERRAFORM_SAMPLE

if TYPE_CHECKING:
    from red_thread_navigate.symbols import FileSymbols

PATH = PurePosixPath('infra/main.tf')


def parse(text: str) -> FileSymbols:
    return TERRAFORM_BACKEND.parse(SourceFile(path=PATH, text=text))


def symbol_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        ('name', 'kind', 'span'),
        [
            pytest.param('var.region', 'variable', (1, 3), id='variable'),
            pytest.param('local.name', 'local', (6, 6), id='local-entry'),
            pytest.param('local.tags', 'local', (7, 7), id='second-local-entry'),
            pytest.param('data.aws_ami.x', 'data', (10, 12), id='data'),
            pytest.param('aws_vpc.this', 'resource', (14, 17), id='resource'),
            pytest.param('module.vpc', 'module', (19, 22), id='module'),
            pytest.param('output.id', 'output', (24, 26), id='output'),
        ],
    )


def reference_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        ('name', 'line'),
        [
            pytest.param('var.region', 6, id='variable'),
            pytest.param('local.name', 7, id='local'),
            pytest.param('local.tags', 16, id='local-in-resource'),
            pytest.param('data.aws_ami.x', 21, id='data'),
            pytest.param('aws_vpc.this', 25, id='resource'),
        ],
    )


class TestSymbols:
    @pytest.fixture
    def parsed(self) -> FileSymbols:
        return parse(TERRAFORM_SAMPLE)

    @symbol_cases()
    def test_each_block_has_its_address_kind_and_span(
        self, parsed: FileSymbols, name: str, kind: str, span: tuple[int, int]
    ) -> None:
        found = {(s.qualified_name, s.kind, s.start_line, s.end_line) for s in parsed.symbols}
        assert (name, kind, *span) in found

    def test_the_locals_block_itself_is_not_a_symbol(self, parsed: FileSymbols) -> None:
        assert len(parsed.symbols) == 7


class TestReferences:
    @reference_cases()
    def test_a_reference_is_named_by_the_address_it_points_at(self, name: str, line: int) -> None:
        found = {(r.name, r.line) for r in parse(TERRAFORM_SAMPLE).references}
        assert (name, line) in found

    def test_attribute_access_past_the_address_is_not_part_of_the_name(self) -> None:
        names = {r.name for r in parse(TERRAFORM_SAMPLE).references}
        assert 'aws_vpc.this.id' not in names

    def test_each_count_and_path_are_not_references(self) -> None:
        text = 'resource "a" "b" {\n  x = each.value\n  y = count.index\n  z = path.module\n}\n'
        assert parse(text).references == ()


class TestSyntaxError:
    def test_keeps_the_valid_blocks_and_adds_a_note_naming_file_and_line(self) -> None:
        text = TERRAFORM_SAMPLE + 'resource "aws_vpc" "bad" {\n  cidr_block =\n}\n'
        parsed = parse(text)
        valid = {symbol.qualified_name for symbol in parse(TERRAFORM_SAMPLE).symbols}
        assert valid <= {symbol.qualified_name for symbol in parsed.symbols}
        assert len(parsed.notes) == 1
        assert str(PATH) in parsed.notes[0]
        assert 'syntax error at line' in parsed.notes[0]

    def test_a_broken_file_still_yields_the_symbols_that_parse(self) -> None:
        parsed = parse(TERRAFORM_BROKEN)
        assert parsed.symbols
        assert len(parsed.notes) == 1


class TestLookup:
    def test_tf_files_pick_the_terraform_backend(self) -> None:
        assert backend_for(PurePosixPath('a/b.tf')) is TERRAFORM_BACKEND

    def test_query_loads_as_a_resource(self) -> None:
        text = (
            resources
            .files('red_thread_navigate.symbols.store')
            .joinpath('queries', 'terraform.scm')
            .read_text(encoding='utf-8')
        )
        assert '@definition.resource' in text


class TestFindReferences:
    @pytest.mark.parametrize(
        ('name', 'lines'),
        [
            pytest.param('local.name', [7], id='local'),
            pytest.param('var.region', [6], id='variable'),
            pytest.param('aws_vpc.this', [25], id='resource'),
            pytest.param('data.aws_ami.x', [21], id='data'),
        ],
    )
    def test_find_matches_the_full_address_a_reference_is_named_by(
        self, name: str, lines: list[int]
    ) -> None:
        file = parse(TERRAFORM_SAMPLE)
        found = references_to((file,), name)
        assert [occurrence.line for occurrence in found] == lines
