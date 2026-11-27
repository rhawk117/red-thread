"""DTO: the struct helpers a record carries, and the frozen keyword-only shape it keeps."""

from dataclasses import dataclass

import msgspec
import pytest
from hypothesis import given
from hypothesis import strategies as st

from tests.core.dto.samples import Sample


@dataclass(slots=True, kw_only=True, frozen=True)
class SampleRow:
    name: str
    count: int
    tags: tuple[str, ...]


class TestStructHelpers:
    sample = Sample(name='queue', count=2, tags=('a', 'b'))
    samples = st.builds(Sample, name=st.text(), count=st.integers(), tags=st.tuples(st.text()))

    def test_as_dict_maps_each_field_to_its_value(self) -> None:
        assert self.sample.as_dict() == {'name': 'queue', 'count': 2, 'tags': ('a', 'b')}

    def test_as_tuple_lists_the_values_in_field_order(self) -> None:
        assert self.sample.as_tuple() == ('queue', 2, ('a', 'b'))

    def test_replace_with_changes_only_the_named_field(self) -> None:
        assert self.sample.replace_with(count=5) == Sample(name='queue', count=5, tags=('a', 'b'))

    def test_replace_with_leaves_the_original_unchanged(self) -> None:
        self.sample.replace_with(name='other')
        assert self.sample.name == 'queue'

    def test_fields_names_every_field_in_order(self) -> None:
        assert [field.name for field in Sample.fields()] == ['name', 'count', 'tags']

    @given(sample=samples)
    def test_convert_rebuilds_a_record_from_its_dict(self, sample: Sample) -> None:
        assert Sample.convert(sample.as_dict()) == sample


class TestConvert:
    def test_a_value_of_the_wrong_type_is_refused(self) -> None:
        with pytest.raises(msgspec.ValidationError):
            Sample.convert({'name': 'queue', 'count': '2'})

    def test_an_unknown_field_is_refused(self) -> None:
        with pytest.raises(msgspec.ValidationError):
            Sample.convert({'name': 'queue', 'extra': 1})

    def test_lax_conversion_coerces_a_numeric_string(self) -> None:
        assert Sample.convert({'name': 'queue', 'count': '2'}, strict=False).count == 2

    def test_from_attributes_reads_the_fields_of_an_object(self) -> None:
        row = SampleRow(name='queue', count=2, tags=('a',))
        assert Sample.convert(row, from_attributes=True) == Sample(
            name='queue', count=2, tags=('a',)
        )


class TestShape:
    sample = Sample(name='queue')

    def test_a_field_cannot_be_set(self) -> None:
        with pytest.raises(AttributeError):
            setattr(self.sample, 'count', 3)  # noqa: B010 - a direct assignment fails ty before the test can show the runtime refusal

    def test_fields_are_keyword_only(self) -> None:
        with pytest.raises(TypeError):
            Sample('queue')  # ty: ignore[missing-argument, too-many-positional-arguments] - the call is wrong on purpose, to show msgspec refuses it
