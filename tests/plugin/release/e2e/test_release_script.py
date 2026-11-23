"""The release script, run as a child process in a repository with a bare origin."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.plugin.release.conftest import ReleaseRepository

TAG = 'v0.1.0'


class TestInitialRelease:
    def test_the_current_version_is_tagged_once_and_only_the_tag_is_pushed(
        self, release_repository: ReleaseRepository
    ) -> None:
        main_before = release_repository.git('rev-parse', 'main', at=release_repository.origin)

        finished = release_repository.release('initial')

        assert finished.code == 0, finished.err
        assert release_repository.git('cat-file', '-t', TAG) == 'tag'
        assert release_repository.git('cat-file', '-t', TAG, at=release_repository.origin) == 'tag'
        assert release_repository.git('tag', '--list', at=release_repository.origin) == TAG
        assert (
            release_repository.git('rev-parse', 'main', at=release_repository.origin) == main_before
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

    def test_an_existing_release_tag_stops_it(self, release_repository: ReleaseRepository) -> None:
        release_repository.git('tag', 'v0.0.1')

        finished = release_repository.release('initial')

        assert finished.code == 1
        assert release_repository.git('tag', '--list') == 'v0.0.1'
        assert release_repository.git('tag', '--list', at=release_repository.origin) == ''

    def test_a_release_tag_on_origin_only_stops_it(
        self, release_repository: ReleaseRepository
    ) -> None:
        release_repository.git('push', 'origin', 'HEAD:refs/tags/v0.0.1')

        finished = release_repository.release('initial')

        assert finished.code == 1
        assert release_repository.git('tag', '--list') == ''

    def test_an_unreadable_origin_stops_it(self, release_repository: ReleaseRepository) -> None:
        missing = release_repository.origin.parent / 'missing.git'
        release_repository.git('remote', 'set-url', 'origin', str(missing))

        finished = release_repository.release('initial')

        assert finished.code != 0
        assert release_repository.git('tag', '--list') == ''

    def test_disagreeing_manifest_and_package_versions_stop_it(
        self, release_repository: ReleaseRepository
    ) -> None:
        release_repository.write_manifest_version('0.2.0')

        finished = release_repository.release('initial')

        assert finished.code == 1
        assert release_repository.git('tag', '--list') == ''
        assert release_repository.git('tag', '--list', at=release_repository.origin) == ''


class TestRecover:
    def test_a_current_version_without_a_tag_stops_it(
        self, release_repository: ReleaseRepository
    ) -> None:
        finished = release_repository.release('recover')

        assert finished.code == 1
        assert 'Previous release tag does not exist' in finished.out + finished.err
