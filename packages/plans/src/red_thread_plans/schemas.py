"""Plan text both ways: the frontmatter as YAML between fences, and the body cut into sections."""

from typing import TYPE_CHECKING

import msgspec
from red_thread_core.frontmatter import FENCE, FenceReasons, decode_yaml, split_frontmatter

from red_thread_plans.domain import (
    HEADING,
    BodyLine,
    Frontmatter,
    PlanDocument,
    Section,
)
from red_thread_plans.errors import PlanShapeError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from red_thread_plans.domain import Outline

LIGHTS_FIELD = '$.lights'
LIGHTS_HINT = (
    'write lights: "on" or lights: "off" with the quotes, because YAML reads a bare on or off'
    ' as true or false'
)
FENCE_REASONS = FenceReasons(
    no_opening='it does not open with a --- line',
    no_closing='its frontmatter has no closing --- line',
)


def number_lines(lines: Sequence[str], start: int) -> tuple[BodyLine, ...]:
    return tuple(BodyLine(number=number, text=text) for number, text in enumerate(lines, start))


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
    decoded = decode_yaml(text, Frontmatter)
    if isinstance(decoded, msgspec.DecodeError):
        return explain_shape(decoded)

    return decoded


def read_plan(text: str) -> PlanDocument | PlanShapeError:
    lines = text.splitlines()
    split = split_frontmatter(lines)
    if isinstance(split, str):
        return PlanShapeError(reason=FENCE_REASONS.explain(split))

    frontmatter = decode_frontmatter('\n'.join(split.front))
    if isinstance(frontmatter, PlanShapeError):
        return frontmatter

    body = number_lines(lines[split.closing + 1 :], split.closing + 2)
    return PlanDocument(frontmatter=frontmatter, sections=cut_sections(body))


def write_plan(frontmatter: Frontmatter, outline: Outline) -> str:
    fields = msgspec.yaml.encode(frontmatter).decode()
    headings = '\n'.join(f'{HEADING}{title}\n' for title in outline.sections)
    return f'{FENCE}\n{fields}{FENCE}\n\n# {frontmatter.title}\n\n{headings}'
