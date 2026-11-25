"""The vendored tree-sitter queries: each carries its upstream license notice and loads."""

from dataclasses import dataclass
from importlib import resources

import pytest

from tests.params import as_params

MIT_NOTICE = 'The MIT License (MIT)'


@dataclass(slots=True, kw_only=True, frozen=True)
class UpstreamNotice:
    name: str
    copyright: str
    marks: tuple[pytest.MarkDecorator, ...] = ()


def query_notice_cases() -> pytest.MarkDecorator:
    notices = (
        UpstreamNotice(name='go', copyright='Copyright (c) 2014 Max Brunsfeld'),
        UpstreamNotice(name='javascript', copyright='Copyright (c) 2014 Max Brunsfeld'),
        UpstreamNotice(name='rust', copyright='Copyright (c) 2017 Maxim Sokolov'),
        UpstreamNotice(name='typescript', copyright='Copyright (c) 2017 Max Brunsfeld'),
    )
    return pytest.mark.parametrize('notice', as_params(notices))


class TestQueryNotice:
    def read_query(self, name: str) -> str:
        return (
            resources
            .files('red_thread_navigate.symbols.store')
            .joinpath('queries', f'{name}.scm')
            .read_text(encoding='utf-8')
        )

    @query_notice_cases()
    def test_query_carries_the_upstream_notice_and_loads_as_a_resource(
        self, notice: UpstreamNotice
    ) -> None:
        text = self.read_query(notice.name)
        assert (notice.copyright in text, MIT_NOTICE in text) == (True, True)
