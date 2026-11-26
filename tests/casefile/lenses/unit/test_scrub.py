"""export: secrets in the selection's title and goal never reach the output."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_casefile.lenses import Selection

from tests.casefile.lenses.builders import create_press_harness, export
from tests.casefile.lenses.cases import lens_name_params, lens_shapes
from tests.casefile.lenses.reading import list_section_lines
from tests.params import as_params

if TYPE_CHECKING:
    from red_thread_casefile.lenses import LensName

    from tests.casefile.lenses.builders import PressHarness

AWS_KEY = 'AKIAIOSFODNN7EXAMPLE'
GITHUB_TOKEN = 'ghp_' + 'a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8'


def lens_name_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize('lens', lens_name_params())


@dataclass(slots=True, kw_only=True, frozen=True)
class SecretScenario:
    name: str
    secret: str
    marker: str
    marks: tuple[pytest.MarkDecorator, ...] = ()


def secret_cases() -> pytest.MarkDecorator:
    scenarios = [
        SecretScenario(name='aws-key', secret=AWS_KEY, marker='[REDACTED:aws-access-key]'),
        SecretScenario(name='github-token', secret=GITHUB_TOKEN, marker='[REDACTED:github-token]'),
    ]
    return pytest.mark.parametrize('scenario', as_params(scenarios))


class TestSelectionScrub:
    @secret_cases()
    def test_secret_in_the_title_is_replaced_in_markdown(
        self, press_harness: PressHarness, scenario: SecretScenario
    ) -> None:
        selection = Selection(title=f'Why {scenario.secret} leaked')

        text = press_harness.export_markdown('brief', selection)

        assert text.splitlines()[0] == f'# Why {scenario.marker} leaked'
        assert scenario.secret not in text

    @secret_cases()
    def test_secret_in_the_goal_is_replaced_in_markdown(
        self, press_harness: PressHarness, scenario: SecretScenario
    ) -> None:
        selection = Selection(goal=f'Rotate {scenario.secret} before friday')

        text = press_harness.export_markdown('brief', selection)

        assert list_section_lines(text, 'Goal') == [f'Rotate {scenario.marker} before friday']
        assert scenario.secret not in text

    @lens_name_cases()
    def test_every_lens_scrubs_the_selection(
        self, press_harness: PressHarness, lens: LensName
    ) -> None:
        selection = Selection(title=f'About {AWS_KEY}', goal=f'Rotate {AWS_KEY}')

        export(press_harness, lens, selection, html=True)

        written = press_harness.snapshot()
        assert set(written) == {f'out/{lens}.md', f'out/{lens}.html'}
        assert all(AWS_KEY not in text for text in written.values())
        assert all('[REDACTED:aws-access-key]' in text for text in written.values())

    def test_a_title_without_a_secret_is_written_as_given(
        self, press_harness: PressHarness
    ) -> None:
        text = press_harness.export_markdown(
            'brief', Selection(title='Why jobs wait', goal='Find out')
        )

        assert text.splitlines()[0] == '# Why jobs wait'
        assert 'REDACTED' not in text


class TestSelectionScrubProperty:
    lenses = st.sampled_from(tuple(shape.name for shape in lens_shapes()))
    aws_keys = st.from_regex(r'AKIA[0-9A-Z]{16}', fullmatch=True)
    words = st.lists(st.text('abcdefgh', min_size=1, max_size=8), min_size=1, max_size=5)
    sentences = words.map(' '.join)

    @given(lens=lenses, key=aws_keys, before=sentences, after=sentences)
    def test_a_key_in_the_title_or_the_goal_reaches_no_written_file(
        self, lens: LensName, key: str, before: str, after: str
    ) -> None:
        harness = create_press_harness()
        selection = Selection(title=f'{before} {key} {after}', goal=f'{after} {key} {before}')

        export(harness, lens, selection, html=True)

        written = harness.snapshot()
        assert set(written) == {f'out/{lens}.md', f'out/{lens}.html'}
        assert all(key not in text for text in written.values())
        assert all('[REDACTED:aws-access-key]' in text for text in written.values())

    @given(lens=lenses, title=sentences, goal=sentences)
    def test_a_title_and_goal_with_no_secret_are_written_as_given(
        self, lens: LensName, title: str, goal: str
    ) -> None:
        harness = create_press_harness()

        text = harness.export_markdown(lens, Selection(title=title, goal=goal))

        assert text.splitlines()[0] == f'# {title}'
        assert goal in text.splitlines()
        assert 'REDACTED' not in text
