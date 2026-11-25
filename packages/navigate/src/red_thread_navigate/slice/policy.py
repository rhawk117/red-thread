"""Refusal policy: the wording of each slice refusal, fitted to the token budget."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

from red_thread_navigate.budget import cut_to_budget, estimate_tokens
from red_thread_navigate.slice.util import (
    MIN_SHOWN,
    cut_steps,
    deep_cut_steps,
    fill,
    shorten_name,
    shorten_path,
)

if TYPE_CHECKING:
    from pathlib import PurePosixPath

OUTSIDE_ROOT_HINT = 'use a path under the root'
MAP_HINT = 'map <path> to see the names there'

type CutSteps = Callable[[str, str], Iterator[tuple[int, int]]]


@dataclass(slots=True, kw_only=True, frozen=True)
class Refused:
    path: PurePosixPath
    budget: int | None = None


@dataclass(slots=True, kw_only=True, frozen=True)
class Wording:
    template: str
    refused: Refused
    name: str

    def fit(self, steps: CutSteps = cut_steps) -> str | None:
        full_path = str(self.refused.path)
        budget = self.refused.budget
        if budget is None:
            return fill(self.template, path=full_path, name=self.name)
        texts = (
            fill(
                self.template,
                path=shorten_path(full_path, path_limit),
                name=shorten_name(self.name, name_limit),
            )
            for path_limit, name_limit in steps(full_path, self.name)
        )
        return next((text for text in texts if estimate_tokens(text) <= budget), None)

    def text(self) -> str:
        if (fitted := self.fit(deep_cut_steps)) is not None:
            return fitted
        shown = fill(
            self.template,
            path=shorten_path(str(self.refused.path), MIN_SHOWN),
            name=shorten_name(self.name, MIN_SHOWN),
        )
        return cut_to_budget(shown, self.refused.budget or 0)


def refusal_text(template: str, *, refused: Refused, name: str) -> str:
    return Wording(template=template, refused=refused, name=name).text()


def unknown_template(nearest: tuple[str, ...]) -> str:
    hint = f'nearest names: {", ".join(nearest)}' if nearest else 'the file has no similar name'
    return f'no symbol <name> in <path>; {hint}'


def unknown_template_with_map_hint(nearest: tuple[str, ...]) -> str:
    return f'{unknown_template(nearest)}. Next step: {MAP_HINT}.'


def hinted_template(plain: str, hint: str, *, refused: Refused) -> str:
    hinted = f'{plain}. Next step: {hint}.'
    fits = Wording(template=hinted, refused=refused, name='').fit() is not None
    return hinted if fits else plain


def file_refused_text(*, refused: Refused, reason: str, hint: str = '') -> str:
    template = f'<path> cannot be sliced: {reason}'
    if hint:
        template = hinted_template(template, hint, refused=refused)
    return refusal_text(template, refused=refused, name='')


def unknown_symbol_text(*, refused: Refused, name: str, nearest: tuple[str, ...]) -> str:
    template = unknown_template(nearest)
    if not nearest:
        mapped = unknown_template_with_map_hint(nearest)
        wording = Wording(template=mapped, refused=refused, name=repr(name))
        template = mapped if wording.fit() is not None else template
    return refusal_text(template, refused=refused, name=repr(name))


def lines_out_of_range_text(*, refused: Refused, start: int, total: int) -> str:
    template = f'<path> has {total} lines, so L{start} is past its end'
    if total:
        template = hinted_template(template, f'slice <path>#L1-L{total}', refused=refused)
    return refusal_text(template, refused=refused, name='')


def outside_root_text(plain: str, *, budget: int) -> str | None:
    message = f'{plain}. Next step: {OUTSIDE_ROOT_HINT}.'
    return message if estimate_tokens(message) <= budget else None


def nearest_candidates(nearest: tuple[str, ...]) -> Iterator[tuple[str, ...]]:
    counts = range(len(nearest), 0, -1)
    yield from (nearest[:count] for count in counts)
    longest = max(map(len, nearest), default=0)
    for count in counts:
        yield from (
            tuple(shorten_name(item, limit) for item in nearest[:count])
            for limit in range(longest, MIN_SHOWN - 1, -1)
        )


def fitted_nearest(*, refused: Refused, name: str, nearest: tuple[str, ...]) -> tuple[str, ...]:
    return next(
        (
            candidate
            for candidate in nearest_candidates(nearest)
            if Wording(template=unknown_template(candidate), refused=refused, name=repr(name)).fit()
            is not None
        ),
        (),
    )
