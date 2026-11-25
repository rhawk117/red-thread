"""Parsing slice addresses and refusing ones outside the root."""

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

import pytest
from hypothesis import given
from hypothesis import strategies as st
from red_thread_navigate.address import (
    ADDRESS_FORMS,
    AddressError,
    LineTarget,
    MalformedAddressError,
    OutsideRootError,
    SymbolTarget,
    parse_address,
)

from tests.params import as_params

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet
    from red_thread_navigate.address import Target

ROOT = Path('/work/repo')


@dataclass(slots=True, kw_only=True, frozen=True)
class FormCase:
    name: str
    text: str
    path: str
    target: Target

    @property
    def param(self) -> ParameterSet:
        return pytest.param(self, id=self.name)


def address_form_cases() -> pytest.MarkDecorator:
    cases = [
        FormCase(
            name='symbol',
            text='src/app.py#handle',
            path='src/app.py',
            target=SymbolTarget(parts=('handle',)),
        ),
        FormCase(
            name='dotted-symbol',
            text='src/app.py#Server.run.inner',
            path='src/app.py',
            target=SymbolTarget(parts=('Server', 'run', 'inner')),
        ),
        FormCase(
            name='one-line',
            text='src/app.py#L12',
            path='src/app.py',
            target=LineTarget(start=12, end=12),
        ),
        FormCase(
            name='line-range',
            text='src/app.py#L12-L20',
            path='src/app.py',
            target=LineTarget(start=12, end=20),
        ),
        FormCase(
            name='one-line-range',
            text='src/app.py#L5-L5',
            path='src/app.py',
            target=LineTarget(start=5, end=5),
        ),
        FormCase(
            name='absolute-inside-root',
            text='/work/repo/src/app.py#run',
            path='src/app.py',
            target=SymbolTarget(parts=('run',)),
        ),
        FormCase(
            name='dotdot-staying-inside',
            text='src/../lib/app.py#run',
            path='lib/app.py',
            target=SymbolTarget(parts=('run',)),
        ),
    ]
    return pytest.mark.parametrize('case', as_params(cases))


def malformed_address_cases() -> pytest.MarkDecorator:
    texts = {
        'no-hash': 'src/app.py',
        'empty-file': '#run',
        'empty-target': 'src/app.py#',
        'empty-segment': 'src/app.py#A..b',
        'leading-dot': 'src/app.py#.b',
        'trailing-dot': 'src/app.py#A.',
        'line-zero': 'src/app.py#L0',
        'range-from-zero': 'src/app.py#L0-L4',
        'range-backwards': 'src/app.py#L9-L3',
        'whitespace': 'src/app.py#a b',
        'names-root': './#run',
    }
    return pytest.mark.parametrize(
        'text', [pytest.param(text, id=name) for name, text in texts.items()]
    )


def outside_root_cases() -> pytest.MarkDecorator:
    return pytest.mark.parametrize(
        'text',
        [
            pytest.param('../x.py#run', id='dotdot'),
            pytest.param('/etc/passwd#L1', id='absolute-outside'),
            pytest.param('/work/repo2/x.py#run', id='sibling-prefix'),
        ],
    )


def lexical_path(steps: list[str]) -> list[str]:
    parts = list(ROOT.parts[1:])
    for step in steps:
        if step == '..':
            parts = parts[:-1]
        elif step != '.':
            parts.append(step)
    return parts


def under_root(steps: list[str]) -> bool:
    parts = lexical_path(steps)
    root_parts = list(ROOT.parts[1:])
    return parts[: len(root_parts)] == root_parts and len(parts) > len(root_parts)


def outside_root(steps: list[str]) -> bool:
    return not under_root(steps)


class TestParseAddress:
    segments = st.sampled_from(('a', 'b', 'src', 'x.py'))
    escaping_depths = st.integers(min_value=0, max_value=4)
    outside_roots = st.sampled_from(('/etc', '/work/repo2', '/work', '/'))
    steps = st.lists(st.sampled_from(('a', 'b', '..', '.')), max_size=8)
    inside_steps = steps.filter(under_root)
    other_steps = steps.filter(outside_root)

    @address_form_cases()
    def test_each_form_parses_to_its_parts(self, case: FormCase) -> None:
        address = parse_address(case.text, root=ROOT)

        assert address.path == PurePosixPath(case.path)
        assert address.target == case.target

    @malformed_address_cases()
    def test_malformed_address_is_refused_with_the_valid_forms(self, text: str) -> None:
        with pytest.raises(MalformedAddressError) as caught:
            parse_address(text, root=ROOT)

        assert all(form in str(caught.value) for form in ADDRESS_FORMS)
        assert '\u2014' not in str(caught.value)

    @outside_root_cases()
    def test_path_outside_the_root_is_refused(self, text: str) -> None:
        with pytest.raises(OutsideRootError):
            parse_address(text, root=ROOT)

    @given(depth=escaping_depths, extra=st.integers(min_value=1, max_value=3), name=segments)
    def test_dotdot_above_the_root_is_refused(self, depth: int, extra: int, name: str) -> None:
        down = '/'.join(['d'] * depth)
        up = '/'.join(['..'] * (depth + extra))
        file = '/'.join(part for part in (down, up, name) if part)

        with pytest.raises(OutsideRootError):
            parse_address(f'{file}#run', root=ROOT)

    @given(base=outside_roots, tail=st.lists(segments, min_size=1, max_size=3))
    def test_absolute_path_outside_the_root_is_refused(self, base: str, tail: list[str]) -> None:
        file = '/'.join([base.rstrip('/'), *tail])

        with pytest.raises(OutsideRootError):
            parse_address(f'{file}#L3', root=ROOT)

    @given(steps=inside_steps, absolute=st.booleans())
    def test_accepted_path_never_leaves_the_root(self, steps: list[str], absolute: bool) -> None:
        file = '/'.join(steps)
        file = f'{ROOT.as_posix()}/{file}' if absolute else file

        address = parse_address(f'{file}#run', root=ROOT)

        assert address.path.parts == tuple(lexical_path(steps)[len(ROOT.parts) - 1 :])
        assert not address.path.is_absolute()
        assert '..' not in address.path.parts

    @given(steps=other_steps, absolute=st.booleans())
    def test_a_path_that_does_not_stay_under_the_root_is_refused(
        self, steps: list[str], absolute: bool
    ) -> None:
        file = '/'.join(steps) or '.'
        file = f'{ROOT.as_posix()}/{file}' if absolute else file

        with pytest.raises(AddressError):
            parse_address(f'{file}#run', root=ROOT)
