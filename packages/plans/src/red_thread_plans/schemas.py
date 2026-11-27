"""Plan text both ways: the frontmatter as YAML between fences, and the body cut into sections."""

from typing import TYPE_CHECKING

from red_thread_core.errors import MalformedDocumentError
from red_thread_core.frontmatter import FENCE, FenceReasons, split_frontmatter
from red_thread_core.lines import cut_at, number_lines

from red_thread_plans.domain import (
    HEADING,
    Frontmatter,
    PlanDocument,
    Section,
)
from red_thread_plans.errors import PlanShapeError

if TYPE_CHECKING:
    from red_thread_core.codec import Codec
    from red_thread_core.lines import Line

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


def cut_sections(lines: tuple[Line, ...]) -> tuple[Section, ...]:
    return tuple(
        Section(
            title=cut.head.text.removeprefix(HEADING).strip(),
            number=cut.head.number,
            lines=cut.body,
        )
        for cut in cut_at(lines, HEADING).parts
    )


def explain_shape(error: MalformedDocumentError) -> PlanShapeError:
    reason = error.reason
    hint = LIGHTS_HINT if LIGHTS_FIELD in reason else None
    return PlanShapeError(reason=reason, hint=hint)


def decode_frontmatter(codec: Codec, text: str) -> Frontmatter | PlanShapeError:
    decoded = codec.decode(text, Frontmatter)
    if isinstance(decoded, MalformedDocumentError):
        return explain_shape(decoded)

    return decoded


def read_plan(codec: Codec, text: str) -> PlanDocument | PlanShapeError:
    lines = text.splitlines()
    split = split_frontmatter(lines)
    if isinstance(split, str):
        return PlanShapeError(reason=FENCE_REASONS.explain(split))

    frontmatter = decode_frontmatter(codec, '\n'.join(split.front))
    if isinstance(frontmatter, PlanShapeError):
        return frontmatter

    body = number_lines(lines[split.closing + 1 :], split.closing + 2)
    return PlanDocument(frontmatter=frontmatter, sections=cut_sections(body))


def write_plan(codec: Codec, frontmatter: Frontmatter, outline: Outline) -> str:
    fields = codec.encode_text(frontmatter)
    headings = '\n'.join(f'{HEADING}{title}\n' for title in outline.sections)
    return f'{FENCE}\n{fields}{FENCE}\n\n# {frontmatter.title}\n\n{headings}'
