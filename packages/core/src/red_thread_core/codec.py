"""Every serialized format behind one Protocol: JSON and YAML to bytes or text, and back."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import msgspec

from red_thread_core.errors import MalformedDocumentError

type Encoded = bytes | str

TEXT_ENCODING = 'utf-8'


@runtime_checkable
class Codec(Protocol):
    def encode(self, value: object) -> bytes: ...

    def encode_text(self, value: object) -> str: ...

    def decode[T](self, data: Encoded, shape: type[T]) -> T | MalformedDocumentError: ...


def as_text(data: bytes) -> str:
    return data.decode(TEXT_ENCODING)


@dataclass(slots=True, kw_only=True, frozen=True)
class JsonCodec:
    def encode(self, value: object) -> bytes:
        return msgspec.json.encode(value)

    def encode_text(self, value: object) -> str:
        return as_text(self.encode(value))

    def decode[T](self, data: Encoded, shape: type[T]) -> T | MalformedDocumentError:
        try:
            return msgspec.json.decode(data, type=shape)
        except msgspec.DecodeError as error:
            return MalformedDocumentError(form='json', reason=str(error))


@dataclass(slots=True, kw_only=True, frozen=True)
class YamlCodec:
    def encode(self, value: object) -> bytes:
        return msgspec.yaml.encode(value)

    def encode_text(self, value: object) -> str:
        return as_text(self.encode(value))

    def decode[T](self, data: Encoded, shape: type[T]) -> T | MalformedDocumentError:
        try:
            return msgspec.yaml.decode(data, type=shape)
        except msgspec.DecodeError as error:
            return MalformedDocumentError(form='yaml', reason=str(error))


def create_json_codec() -> Codec:
    return JsonCodec()


def create_yaml_codec() -> Codec:
    return YamlCodec()
