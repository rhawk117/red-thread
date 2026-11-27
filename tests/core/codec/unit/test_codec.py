"""The codecs: what they encode decodes back, and a malformed document is a returned error."""

from datetime import date

import msgspec
import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_core.codec import Codec, create_json_codec, create_yaml_codec
from red_thread_core.errors import MalformedDocumentError


class Header(msgspec.Struct, frozen=True, kw_only=True, forbid_unknown_fields=True):
    title: str
    created: date
    tags: tuple[str, ...] = ()


def codec_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        'codec',
        [
            pytest.param(create_json_codec(), id='json'),
            pytest.param(create_yaml_codec(), id='yaml'),
        ],
    )


def malformed_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        ('codec', 'form', 'text'),
        [
            pytest.param(create_json_codec(), 'json', '{"title": ', id='json-syntax'),
            pytest.param(create_yaml_codec(), 'yaml', 'title: [', id='yaml-syntax'),
            pytest.param(create_json_codec(), 'json', '{"title": 3}', id='json-shape'),
            pytest.param(create_yaml_codec(), 'yaml', 'title: a\nextra: 1', id='yaml-shape'),
        ],
    )


class TestCodec:
    headers = st.builds(
        Header,
        title=st.text(),
        created=st.dates(),
        tags=st.lists(st.text(max_size=8), max_size=3).map(tuple),
    )

    @codec_cases()
    def test_each_codec_is_a_codec(self, codec: Codec) -> None:
        assert isinstance(codec, Codec)

    @codec_cases()
    @given(header=headers)
    def test_an_encoded_value_decodes_back(self, codec: Codec, header: Header) -> None:
        assert codec.decode(codec.encode(header), Header) == header

    @codec_cases()
    @given(header=headers)
    def test_text_is_the_utf8_of_the_bytes(self, codec: Codec, header: Header) -> None:
        assert codec.encode_text(header).encode('utf-8') == codec.encode(header)

    @codec_cases()
    @given(header=headers)
    def test_text_decodes_back(self, codec: Codec, header: Header) -> None:
        assert codec.decode(codec.encode_text(header), Header) == header

    @malformed_cases()
    def test_a_malformed_document_is_a_returned_error_naming_its_form(
        self, codec: Codec, form: str, text: str
    ) -> None:
        decoded = codec.decode(text, Header)

        assert isinstance(decoded, MalformedDocumentError)
        assert decoded.form == form

    def test_a_shape_error_keeps_the_path_of_the_field(self) -> None:
        decoded = create_yaml_codec().decode('title: 3\ncreated: 2026-11-27', Header)

        assert isinstance(decoded, MalformedDocumentError)
        assert '$.title' in decoded.reason
