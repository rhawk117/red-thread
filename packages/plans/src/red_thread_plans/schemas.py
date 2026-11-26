"""Plan text both ways: the frontmatter as YAML between fences, and the body cut into sections."""

from typing import TYPE_CHECKING

import msgspec

from red_thread_plans.domain import (
    FENCE,
    HEADING,
    SECTIONS,
    BodyLine,
    Frontmatter,
    PlanDocument,
    Section,
)
from red_thread_plans.errors import PlanShapeError

if TYPE_CHECKING:
    from collections.abc import Sequence

LIGHTS_FIELD = '$.lights'
LIGHTS_HINT = (
    'write lights: "on" or lights: "off" with the quotes, because YAML reads a bare on or off'
    ' as true or false'
)


def number_lines(lines: Sequence[str], start: int) -> tuple[BodyLine, ...]:
    return tuple(BodyLine(number=number, text=text) for number, text in enumerate(lines, start))


def find_closing_fence(lines: Sequence[str]) -> int | None:
    found = (index for index, line in enumerate(lines) if index and line.strip() == FENCE)
    return next(found, None)


def cut_sections(lines: tuple[BodyLine, ...]) -> tuple[Section, ...]:
    starts = [index for index, line in enumerate(lines) if line.text.startswith(HEADING)]
    ends = [*starts[1:], len(lines)]
    return tuple(
        Section(
            title=lines[start].text.removeprefix(HEADING).strip(),
            number=lines[start].number,
            lines=lines[start + 1 : end],
        )
        for start, end in zip(starts, ends, strict=True)
    )


def explain_shape(error: msgspec.DecodeError) -> PlanShapeError:
    reason = str(error)
    hint = LIGHTS_HINT if LIGHTS_FIELD in reason else None
    return PlanShapeError(reason=reason, hint=hint)


def decode_frontmatter(text: str) -> Frontmatter | PlanShapeError:
    try:
        return msgspec.yaml.decode(text, type=Frontmatter)
    except msgspec.DecodeError as error:
        return explain_shape(error)


def read_plan(text: str) -> PlanDocument | PlanShapeError:
    lines = text.splitlines()
    if not lines or lines[0].strip() != FENCE:
        return PlanShapeError(reason='it does not open with a --- line')

    closing = find_closing_fence(lines)
    if closing is None:
        return PlanShapeError(reason='its frontmatter has no closing --- line')

    frontmatter = decode_frontmatter('\n'.join(lines[1:closing]))
    if isinstance(frontmatter, PlanShapeError):
        return frontmatter

    body = number_lines(lines[closing + 1 :], closing + 2)
    return PlanDocument(frontmatter=frontmatter, sections=cut_sections(body))


def write_plan(frontmatter: Frontmatter) -> str:
    fields = msgspec.yaml.encode(frontmatter).decode()
    headings = '\n'.join(f'{HEADING}{title}\n' for title in SECTIONS)
    return f'{FENCE}\n{fields}{FENCE}\n\n# {frontmatter.title}\n\n{headings}'
