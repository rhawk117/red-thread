"""The frozen base of every record that crosses a wire, with msgspec's struct helpers as methods."""

from typing import TYPE_CHECKING, Any, Self, TypedDict, Unpack

import msgspec

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

type DecodeHook = Callable[[type[Any], Any], Any]


class ConversionOptions(TypedDict, total=False):
    strict: bool
    from_attributes: bool
    dec_hook: DecodeHook | None
    builtin_types: Iterable[type[Any]] | None
    str_keys: bool


class DTO(msgspec.Struct, frozen=True, kw_only=True):
    def as_dict(self) -> dict[str, Any]:
        return msgspec.structs.asdict(self)

    def as_tuple(self) -> tuple[Any, ...]:
        return msgspec.structs.astuple(self)

    def replace_with(self, **changes: Any) -> Self:
        return msgspec.structs.replace(self, **changes)

    @classmethod
    def fields(cls) -> tuple[msgspec.structs.FieldInfo, ...]:
        return msgspec.structs.fields(cls)

    @classmethod
    def convert(cls, obj: object, /, **options: Unpack[ConversionOptions]) -> Self:
        return msgspec.convert(obj, cls, **options)
