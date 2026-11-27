"""The selection an export reads: which entries a lens shows, and its title and goal."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeIs

from red_thread_core.errors import MalformedDocumentError

from red_thread_casefile.errors import MalformedSelectionError
from red_thread_casefile.lenses import Selection

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from red_thread_core.codec import Codec


def find_unknown_field(record: Mapping[str, object], allowed: tuple[str, ...]) -> str | None:
    return next((name for name in record if name not in allowed), None)


def find_non_string(record: Mapping[str, object], names: Iterable[str]) -> str | None:
    return next((name for name in names if not isinstance(record[name], str)), None)


def read_text(record: Mapping[str, object], name: str) -> str | None:
    value = record.get(name)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


SELECTION_TEXT_FIELDS = ('title', 'goal')
SELECTION_REF_FIELDS = ('include', 'blocking')


def is_json_object(value: object) -> TypeIs[dict[str, object]]:
    return isinstance(value, dict)


def is_ref_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(ref, str) for ref in value)


@dataclass(slots=True, kw_only=True, frozen=True)
class SelectionRecord:
    record: Mapping[str, object]

    @property
    def unknown_field(self) -> str | None:
        return find_unknown_field(self.record, (*SELECTION_TEXT_FIELDS, *SELECTION_REF_FIELDS))

    @property
    def malformed_text_field(self) -> str | None:
        present = (name for name in SELECTION_TEXT_FIELDS if name in self.record)
        return find_non_string(self.record, present)

    @property
    def malformed_ref_field(self) -> str | None:
        present = (name for name in SELECTION_REF_FIELDS if name in self.record)
        return next((name for name in present if not is_ref_list(self.record[name])), None)

    def get_shape_problem(self) -> MalformedSelectionError | None:
        if (unknown := self.unknown_field) is not None:
            return MalformedSelectionError(reason=f'{unknown} is not a selection key')

        if (malformed := self.malformed_text_field) is not None:
            return MalformedSelectionError(reason=f'{malformed} must be a string')

        if (malformed := self.malformed_ref_field) is not None:
            return MalformedSelectionError(reason=f'{malformed} must be a list of entry refs')

        return None

    def read_refs(self, name: str) -> tuple[str, ...] | None:
        value = self.record.get(name)
        if not isinstance(value, list):
            return None
        return tuple(ref for ref in value if isinstance(ref, str))

    def parse(self) -> Selection:
        return Selection(
            title=read_text(self.record, 'title'),
            goal=read_text(self.record, 'goal'),
            include=self.read_refs('include'),
            blocking=self.read_refs('blocking'),
        )


def load_selection(codec: Codec, text: str) -> SelectionRecord | MalformedSelectionError:
    if not text.strip():
        return SelectionRecord(record={})

    loaded = codec.decode(text, object)
    if isinstance(loaded, MalformedDocumentError):
        return MalformedSelectionError(reason=f'it is not JSON ({loaded.reason})')

    if not is_json_object(loaded):
        return MalformedSelectionError(reason='it is not a JSON object')
    return SelectionRecord(record=loaded)
