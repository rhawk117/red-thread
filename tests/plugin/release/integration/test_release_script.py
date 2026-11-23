"""The release script, run as a child process in a repository with a bare origin."""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tests.plugin.release.repository import ReleaseRepository

TAG = 'v0.1.0'


class TestInitialRelease:
    @pytest.fixture
    def origin_main_before(self, release_repository: ReleaseRepository) -> str:
        return release_repository.git('rev-parse', 'main', at=release_repository.origin)

    def test_the_current_version_is_tagged_once_and_only_the_tag_is_pushed(
        self, release_repository: ReleaseRepository, origin_main_before: str
    ) -> None:
        finished = release_repository.release('initial')

        assert finished.code == 0, finished.err
        assert release_repository.git('cat-file', '-t', TAG) == 'tag'
        assert release_repository.git('cat-file', '-t', TAG, at=release_repository.origin) == 'tag'
        assert release_repository.git('tag', '--list', at=release_repository.origin) == TAG
        assert (
            release_repository.git('rev-parse', 'main', at=release_repository.origin)
            == origin_main_before
        )
        assert release_repository.git('status', '--porcelain') == ''
        assert (
            release_repository.output.read_text(encoding='utf-8') == f'version=0.1.0\ntag={TAG}\n'
        )

    def test_the_tag_is_made_by_the_release_bot(
        self, release_repository: ReleaseRepository
    ) -> None:
        release_repository.release('initial')

        tagger = release_repository.git(
            'for-each-ref', '--format=%(taggername)', f'refs/tags/{TAG}'
        )

        assert tagger == 'github-actions[bot]'


class TestInitialReleaseRefusal:
    @pytest.fixture
    def locally_tagged(self, release_repository: ReleaseRepository) -> ReleaseRepository:
        release_repository.git('tag', 'v0.0.1')
        return release_repository

    @pytest.fixture
    def origin_tagged(self, release_repository: ReleaseRepository) -> ReleaseRepository:
        release_repository.git('push', 'origin', 'HEAD:refs/tags/v0.0.1')
        return release_repository

    @pytest.fixture
    def unreadable_origin(self, release_repository: ReleaseRepository) -> ReleaseRepository:
        missing = release_repository.origin.parent / 'missing.git'
        release_repository.git('remote', 'set-url', 'origin', str(missing))
        return release_repository

    @pytest.fixture
    def mismatched_manifest(self, release_repository: ReleaseRepository) -> ReleaseRepository:
        release_repository.write_manifest_version('0.2.0')
        return release_repository

    def assert_stopped_without_tags(self, repository: ReleaseRepository, message: str) -> None:
        local_before = repository.git('tag', '--list')
        origin_before = repository.git('tag', '--list', at=repository.origin)

        finished = repository.release('initial')

        assert finished.code == 1
        assert message in finished.out + finished.err
        assert repository.git('tag', '--list') == local_before
        assert repository.git('tag', '--list', at=repository.origin) == origin_before

    def test_an_existing_release_tag_stops_it(self, locally_tagged: ReleaseRepository) -> None:
        self.assert_stopped_without_tags(
            locally_tagged, 'The initial release requires a repository without release tags.'
        )

    def test_a_release_tag_on_origin_only_stops_it(self, origin_tagged: ReleaseRepository) -> None:
        self.assert_stopped_without_tags(
            origin_tagged, 'The initial release requires an origin without release tags.'
        )

    def test_an_unreadable_origin_stops_it(self, unreadable_origin: ReleaseRepository) -> None:
        self.assert_stopped_without_tags(unreadable_origin, 'Cannot read release tags from origin.')

    def test_disagreeing_manifest_and_package_versions_stop_it(
        self, mismatched_manifest: ReleaseRepository
    ) -> None:
        self.assert_stopped_without_tags(
            mismatched_manifest, 'Plugin manifest and package versions differ.'
        )


class TestRecover:
    def test_a_current_version_without_a_tag_stops_it(
        self, release_repository: ReleaseRepository
    ) -> None:
        finished = release_repository.release('recover')

        assert finished.code == 1
        assert 'Previous release tag does not exist' in finished.out + finished.err
